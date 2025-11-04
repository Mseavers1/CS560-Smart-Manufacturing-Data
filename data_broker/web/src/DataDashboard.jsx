import { useEffect, useRef, useState } from "react";

export default function DataDashboard() {

    const [activeSession, setActiveSession] = useState(false);

    const startSession = async () => {
        try {
            const now = new Date();
            const label = "ses_" + now.toISOString();
            const encodedLabel = encodeURIComponent(label);
            const res = await fetch(`http://192.168.1.76:8000/session/start/${encodedLabel}`);
            const data = await res.json();

            if (data.success) {
                alert("success")
                setActiveSession(true);
            } else {
                alert("failed")
                alert(data.error)
            }
        } catch (err) {
            alert(err)
        }
    };

    const stopSession = async () => {
        try {
            const res = await fetch(`http://192.168.1.76:8000/session/stop/`);
            const data = await res.json();

            if (data.success) {
                setActiveSession(false);
            } else {
                
            }
        } catch (err) {
            
        }
    };

    function CameraMessage() {
        const [lines, setLines] = useState([]);
        const boxRef = useRef(null);

        useEffect(() => {
            const ws = new WebSocket("ws://192.168.1.76:8000/ws/camera");

            ws.onmessage = (event) => {
            setLines((prev) => {
                const next = [...prev, event.data];
                return next.length > 500 ? next.slice(-500) : next;
            });
            };

            ws.onopen  = () => setLines((p) => [...p, "[client] connected"]);
            ws.onclose = () => setLines((p) => [...p, "[client] disconnected"]);
            ws.onerror = () => setLines((p) => [...p, "[client] error"]);

            return () => ws.close();
        }, []);

        useEffect(() => {
            boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight, behavior: "auto" });
        }, [lines]);

        return (
            <div className="bg-white rounded-lg shadow p-5">
            <h3 className="text-lg font-semibold mb-2">Camera Messages</h3>
            <div
                ref={boxRef}
                className="bg-gray-900 font-mono text-sm rounded-md p-3 h-64 overflow-y-auto text-left w-full"
            >
                {lines.map((line, i) => (
                <p key={i} className="whitespace-pre-wrap break-words w-full text-green-400">
                    {line}
                </p>
                ))}
            </div>
            </div>
        );
    }



    return (
        <div>
            
            {/* 2nd Top Bar -- Turn on and off a session */}
            <div className="fixed top-14 left-0 w-full flex justify-between items-center px-6 py-1 bg-gray-500 text-white shadow z-30">
                <h2 className="text-base font-medium">Data Dashboard</h2>

                <div className="flex gap-2">
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
                    disabled={!activeSession}
                    >
                    Stop Session
                    </button>
                </div>
            </div>

            <div className='flex flex-col items-center pt-16 gap-5'>

                <div className='flex flex-row items-center gap-5'>
                    
                    <CameraMessage/>                    

                    <div className="bg-white rounded-lg shadow p-5">
                        <h3 className="text-lg font-semibold mb-2">IMU Messages</h3>
                        <div className="bg-gray-900 text-green-400 font-mono text-sm rounded-md p-3 h-64 overflow-y-auto text-left w-full">
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:32] Camera 1 initialized</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:33] Streaming started (1920x1080 @ 60fps)</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:35] Frame captured (latency: 8ms)</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:36] Frame captured (latency: 9ms)</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:37] Warning: dropped frame</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:38] Frame captured (latency: 10ms)</p>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-5">
                        <h3 className="text-lg font-semibold mb-2">Robot Messages</h3>
                        <div className="bg-gray-900 text-green-400 font-mono text-sm rounded-md p-3 h-64 overflow-y-auto text-left w-full">
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:32] Camera 1 initialized</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:33] Streaming started (1920x1080 @ 60fps)</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:35] Frame captured (latency: 8ms)</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:36] Frame captured (latency: 9ms)</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:37] Warning: dropped frame</p>
                            <p className='whitespace-pre-wrap break-words w-full'>[12:01:38] Frame captured (latency: 10ms)</p>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-lg shadow p-5">
                    <h3 className="text-lg font-semibold mb-2">Global Errors</h3>
                    <div className="bg-gray-900 text-green-400 font-mono text-sm rounded-md p-3 h-64 overflow-y-auto text-left w-full">
                        <p className='whitespace-pre-wrap break-words w-full'>[12:01:32] Camera 1 initialized</p>
                        <p className='whitespace-pre-wrap break-words w-full'>[12:01:33] Streaming started (1920x1080 @ 60fps)</p>
                        <p className='whitespace-pre-wrap break-words w-full'>[12:01:35] Frame captured (latency: 8ms)</p>
                        <p className='whitespace-pre-wrap break-words w-full'>[12:01:36] Frame captured (latency: 9ms)</p>
                        <p className='whitespace-pre-wrap break-words w-full'>[12:01:37] Warning: dropped frame</p>
                        <p className='whitespace-pre-wrap break-words w-full'>[12:01:38] Frame captured (latency: 10ms)</p>
                    </div>
                </div>


            </div>


        </div>
    )


}