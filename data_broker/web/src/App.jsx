import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import HomePage from './Home.jsx';
import DataDashboard from './DataDashboard.jsx'
import {Routes, Route, Link, useNavigate} from "react-router-dom";


import './App.css'

function App() {
  
  const nav = useNavigate();

  function topBar() {


    return (
      <nav className="fixed top-0 left-0 w-full justify-between items-center px-6 py-3 bg-gray-800 text-white shadow z-40">

        <div className="flex flex-row justify-between items-center">

          <h2 className="text-lg font-semibold">Smart Manufacturing Research</h2>

          <div className="flex items-center gap-4 relative">

            <button className="flex items-center gap-1 text-white bg-blue-600 hover:bg-blue-500 p-1 rounded cursor-pointer active:scale-95 transition-transform duration-100" onClick={() => {nav("/");}}>
                Home    
            </button>

            <button className="flex items-center gap-1 text-white bg-blue-600 hover:bg-blue-500 p-1 rounded cursor-pointer active:scale-95 transition-transform duration-100" onClick={() => {nav("/data/dashboard");}}>
                Data Dashboard    
            </button>
          
            <div className="relative group">
          
              <button className="flex items-center gap-1 text-white bg-blue-600 hover:bg-blue-500 p-1 rounded cursor-pointer active:scale-95 transition-transform duration-100">
                AI
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 10.94l3.71-3.71a.75.75 0 1 1 1.06 1.06l-4.24 4.24a.75.75 0 0 1-1.06 0L5.21 8.29a.75.75 0 0 1 .02-1.08z" />
                </svg>
              </button>

              <div className="absolute left-0 mt-2 min-w-40 rounded-md bg-white text-gray-800 shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                <Link
                  to="/ai/dashboard"
                  className="block px-4 py-2 hover:bg-gray-100 rounded-t-md"
                >
                  Dashboard
                </Link>
              </div>
            </div>

            <div className="relative group">
          
              <button className="flex items-center gap-1 text-white p-1 rounded bg-blue-600 hover:bg-blue-500 cursor-pointer active:scale-95 transition-transform duration-100">
                Twins
                <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 10.94l3.71-3.71a.75.75 0 1 1 1.06 1.06l-4.24 4.24a.75.75 0 0 1-1.06 0L5.21 8.29a.75.75 0 0 1 .02-1.08z" />
                </svg>
              </button>

              <div className="absolute left-0 mt-2 min-w-40 rounded-md bg-white text-gray-800 shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                <Link
                  to="/twins/dashboard"
                  className="block px-4 py-2 hover:bg-gray-100 rounded-t-md"
                >
                  Dashboard
                </Link>
              </div>
            </div>

          </div>
        </div>
      </nav>
    )
  }

  return (
   <div className='min-h-screen bg-gray-100'>

      {topBar()}

      {/* Routes */}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/data/dashboard" element={<DataDashboard />} />
      </Routes>
    </div>
  )
}

export default App
