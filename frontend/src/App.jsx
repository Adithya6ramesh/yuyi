// Which page shows for which address.
import { Route, Routes } from 'react-router-dom'
import Desk from './pages/Desk.jsx'
import Landing from './pages/Landing.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/desk" element={<Desk />} />
      <Route path="*" element={<Landing />} />
    </Routes>
  )
}
