import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { it, expect, vi } from "vitest"
import PlacementTest from "../PlacementTest"

vi.mock("../../api/client", () => ({
  createUser: vi.fn(async () => ({ user_id: 2 })), getUser: vi.fn(),
  startPlacementTest: vi.fn(async () => ({ questions: [] })), submitPlacementTest: vi.fn(),
  setUserId: vi.fn(), getUserId: vi.fn(() => 1), listAccounts: vi.fn(async () => ({ accounts: [] })),
}))
vi.mock("../../hooks/useLanguage", () => ({ useLanguage: () => ({ t: k => k }) }))

it("signed-in account whose fetch fails transiently (network/401) must not create a new account", async () => {
  const { getUser, createUser } = await import("../../api/client")
  localStorage.setItem("userName", "Anna")
  getUser.mockRejectedValue(new Error("Failed to fetch"))
  render(<MemoryRouter><PlacementTest /></MemoryRouter>)
  await waitFor(() => expect(getUser).toHaveBeenCalled())
  await userEvent.setup().click(screen.getByRole("button", { name: /place.startTest/i }))
  await waitFor(() => expect(createUser).not.toHaveBeenCalled())
})

it("click before the account loads must not create a new account", async () => {
  const { getUser, createUser } = await import("../../api/client")
  createUser.mockClear()
  localStorage.setItem("userName", "Anna")
  getUser.mockReturnValue(new Promise(() => {}))
  render(<MemoryRouter><PlacementTest /></MemoryRouter>)
  await userEvent.setup().click(screen.getAllByRole("button", { name: /place.startTest/i }).at(-1))
  await new Promise(r => setTimeout(r, 50))
  expect(createUser).not.toHaveBeenCalled()
})

it("a retry after a failed start does not create a second account", async () => {
  const { getUser, createUser, startPlacementTest, getUserId } = await import("../../api/client")
  createUser.mockClear()
  getUserId.mockReturnValue(null)
  getUser.mockReset()
  localStorage.setItem("userName", "Anna")
  startPlacementTest.mockRejectedValueOnce(new Error("AI service unavailable"))
  render(<MemoryRouter><PlacementTest /></MemoryRouter>)
  const user = userEvent.setup()
  const start = () => screen.getAllByRole("button", { name: /place.startTest/i }).at(-1)
  await user.click(start())
  await waitFor(() => expect(startPlacementTest).toHaveBeenCalledTimes(1))
  await user.click(start())
  await waitFor(() => expect(startPlacementTest).toHaveBeenCalledTimes(2))
  expect(createUser).toHaveBeenCalledTimes(1)
})
