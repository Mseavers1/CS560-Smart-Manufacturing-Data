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
          
               <div className="relative group">
          
              <a
                href="http://192.168.1.76:3000/"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-white p-1 rounded bg-blue-600 hover:bg-blue-500 cursor-pointer active:scale-95 transition-transform duration-100"
              >
                AI
              </a>

            </div>
            
            </div>

            <div className="relative group">
          
              <a
                href="http://192.168.1.76:8001/"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-white p-1 rounded bg-blue-600 hover:bg-blue-500 cursor-pointer active:scale-95 transition-transform duration-100"
              >
                Twins
              </a>

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
