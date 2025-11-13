import { useEffect, useRef, useState } from "react";
import MessageWB from "./components/MessageWB";
import StatusIndicator from "./components/StatusIndicator";
import BackupCard from "./components/BackupCard";

export default function DataDashboard() {

    const [activeSession, setActiveSession] = useState(false);
    const [isStopping, setIsStopping] = useState(false);

    useEffect(() => {

        const getStatus = async () => {
            try {
            const r = await fetch("http://192.168.1.76:8000/session");
            const json = await r.json();
            setActiveSession(json.data);
            } catch (e) {
            sendMessage("camera", "error", "An unexpected error has occurred: " + e);
            }
        };

        getStatus();
    }, []);

    const sendMessage = async (dest, type, msg) => {
        
        try {
            await fetch("http://192.168.1.76:8000/send/" + dest, {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({ type: type, text: msg })
            });

        } catch (err) {
            alert(err)
        }

    }

    const startSession = async () => {

        sendMessage("misc", "info", "Starting new session...")

        try {
            const now = new Date();
            const label = "ses_" + now.toISOString();
            const encodedLabel = encodeURIComponent(label);
            const res = await fetch(`http://192.168.1.76:8000/session/start/${encodedLabel}`);
            const data = await res.json();

            if (data.success) {
                setActiveSession(true);
                sendMessage("misc", "info", "Session ready");
            } else {
                sendMessage("misc", "error", "Failed to start session: " + data.error);
            }
        } catch (err) {
            sendMessage("misc", "error", "An unexpected error has occured: " + err);
        }
    };

    const stopSession = async () => {

        sendMessage("misc", "info", "Stopping the current session...");
        setIsStopping(true);

        try {
            const res = await fetch(`http://192.168.1.76:8000/session/stop/`);
            const data = await res.json();

            if (data.success) {
                sendMessage("misc", "info", "Session Stopped");
                setActiveSession(false);
            } else {
                sendMessage("misc", "error", "Failed to stop the session: " + data.error);
            }

        } catch (err) {
            sendMessage("misc", "error", "An unexpected error has occured: " + err)
            
        } finally {
            setIsStopping(false)
        }
    };

    return (
        <div className="h-screen">
            
            {/* 2nd Top Bar -- Turn on and off a session */}
            <div className="fixed top-14 left-0 w-full flex justify-between items-center px-6 py-1 bg-gray-500 text-white shadow z-30">
                <h2 className="text-base font-medium">Data Dashboard</h2>

                <div className="flex gap-4">

                    <button className="flex items-center gap-1 text-white bg-blue-500 hover:bg-blue-600 text-sm px-2 py-1 rounded font-semibold leading-tight cursor-pointer active:scale-95 transition-transform duration-100 disabled:bg-gray-400 disabled:cursor-not-allowed"
                     onClick={() => window.open("http://192.168.1.111:8080", "_blank")}>
                        Open Database GUI
                    </button>


                    <button
                    className="flex items-center gap-1 text-white bg-green-500 hover:bg-green-600 text-sm px-2 py-1 rounded font-semibold leading-tight cursor-pointer active:scale-95 transition-transform duration-100 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    disabled={activeSession}
                    onClick={() => startSession()}
                    >
                    Start Session
                    </button>

                    <button
                    className="flex items-center gap-1 text-white bg-red-500 hover:bg-red-600 text-sm px-2 py-1 rounded font-semibold leading-tight cursor-pointer active:scale-95 transition-transform duration-100 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    onClick={() => stopSession()}
                    disabled={!activeSession || isStopping}
                    >
                    Stop Session
                    </button>

                    <StatusIndicator active={activeSession} onMsg="Session Active" offMsg="Session Inactive"/>
                </div>
            </div>

            <div className='flex flex-col items-center pt-16 gap-5 justify-center'>

                <div className='flex flex-row items-center gap-5'>
                    
                    <MessageWB type="camera"/>
                    <MessageWB type="imu"/>
                    <MessageWB type="robot"/>  

                </div>

                <div className='flex flex-row items-center gap-5'>
                    
                    <MessageWB type="misc" />
                    <BackupCard sendMessage={sendMessage}/> 

                </div>


            </div>


        </div>
    )


}