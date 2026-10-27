import '@testing-library/jest-dom/vitest'
import { configure } from '@testing-library/react'

// waitFor/findBy wait 1 s by default; on a busy PC (backend tests and model
// calls running at the same time, 27.10) one test once missed that limit.
// 5 s only matters when the test would otherwise fail.
configure({ asyncUtilTimeout: 5000 })
