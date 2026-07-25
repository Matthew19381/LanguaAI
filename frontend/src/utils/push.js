/**
 * Browser push subscription flow.
 *
 * Turning push on: fetch the server's VAPID public key, ask permission, subscribe
 * through the service worker's PushManager, and register the subscription with
 * the backend. Turning it off: unsubscribe locally and tell the backend to drop it.
 */
import { getVapidPublicKey, subscribePush, unsubscribePush } from '../api/client'

/** Web Push needs a service worker, the Push API and the Notifications API. */
export function pushSupported() {
  return (
    typeof navigator !== 'undefined' &&
    'serviceWorker' in navigator &&
    typeof window !== 'undefined' &&
    'PushManager' in window &&
    'Notification' in window
  )
}

/** VAPID public keys are base64url; PushManager wants a Uint8Array. */
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const out = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i)
  return out
}

/** True if this browser already has an active push subscription. */
export async function isSubscribed() {
  if (!pushSupported()) return false
  try {
    const reg = await navigator.serviceWorker.ready
    return Boolean(await reg.pushManager.getSubscription())
  } catch {
    return false
  }
}

/**
 * Enable push for a user. Resolves true on success; throws an Error whose message
 * is one of: 'unsupported', 'disabled' (no VAPID keys server-side), 'denied'.
 */
export async function enablePush(userId) {
  if (!pushSupported()) throw new Error('unsupported')

  const { enabled, public_key } = await getVapidPublicKey()
  if (!enabled || !public_key) throw new Error('disabled')

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') throw new Error('denied')

  const reg = await navigator.serviceWorker.ready
  let sub = await reg.pushManager.getSubscription()
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(public_key),
    })
  }
  await subscribePush(userId, sub.toJSON())
  return true
}

/** Disable push: unsubscribe in the browser and drop the row server-side. */
export async function disablePush() {
  if (!pushSupported()) return true
  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.getSubscription()
  if (sub) {
    await unsubscribePush(sub.endpoint).catch(() => {})
    await sub.unsubscribe().catch(() => {})
  }
  return true
}
