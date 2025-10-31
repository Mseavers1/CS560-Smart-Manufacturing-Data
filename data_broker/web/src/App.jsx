import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import HomePage from './Home.jsx';
import DataDashboard from './DataDashboard.jsx'
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";


import './App.css'

function App() {
  

  return (
   <BrowserRouter>

      {/* Topbar */}
      <nav className="navbar">
        <h2 className="title">Smart Manufacturing Research</h2>
        <div className="nav-links">
          <Link to="/">Home</Link>
          <Link to="/data/dashboard">Data Dashboard</Link>
        </div>
      </nav>

      {/* Routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/data/dashboard" element={<DataDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
