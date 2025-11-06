    import { useEffect, useRef, useState } from "react";
    import StatusIndicator from "./StatusIndicator";
    
    export default function MessageWB({type}) {
        const [lines, setLines] = useState([]);
        const [connected, setConnected] = useState(false);
        const [refreshTemp, setRefreshTemp] = useState(false)

        const boxRef = useRef(null);

        const capitalizeType = type.charAt(0).toUpperCase() + type.slice(1);

        useEffect(() => {
            const ws = new WebSocket("ws://192.168.1.76:8000/ws/" + type);

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data); 

                    if (data && data.type && data.text) {
                        setLines((prev) => {
                            const next = [...prev, data];
                            return next.length > 500 ? next.slice(-500) : next;
                        });
                    } else {

                        setLines((prev) => {
                            const next = [...prev, { text: event.data, type: "normal" }];
                            return next.length > 500 ? next.slice(-500) : next;
                        });
                    }
                } catch (err) {

                    setLines((prev) => {
                        const next = [...prev, { text: event.data, type: "normal" }];
                        return next.length > 500 ? next.slice(-500) : next;
                    });
                }
            };


            ws.onopen = () => {
                setConnected(true);
            }

            ws.onclose = () => {
                setConnected(false);
            }

            ws.onerror = () => {
                setConnected(false);
            }

            return () => ws.close();
        }, [refreshTemp]);

        useEffect(() => {
            boxRef.current?.scrollTo({
                top: boxRef.current.scrollHeight,
                behavior: "auto",
            });
        }, [lines]);

        return (
            <div className="bg-white rounded-lg shadow p-5 w-[550px] gap-2">
                <h3 className="text-lg font-semibold mb-2"> {capitalizeType} Messages</h3>
                <div
                    ref={boxRef}
                    className="bg-gray-900 font-mono text-sm rounded-md p-3 h-64 overflow-y-auto overflow-x-auto whitespace-pre text-left w-full"
                >
                    {lines.map((line, i) => (
                        <p
                            key={i}
                            className={`whitespace-pre w-full ${
                                line.type === "error"
                                    ? "text-red-400"
                                    : line.type === "info"
                                    ? "text-yellow-400"
                                    : "text-green-400"
                            }`}
                        >
                            [{line.timestamp}] {line.text}
                        </p>
                    ))}
                </div>

                <div className="flex flex-row justify-between items-center mt-4">

                    <StatusIndicator active={connected} onMsg="Listening" offMsg="Disconnected" />


                    <div className="flex flex-row items-center gap-3">
                        
                        <button
                            className="flex items-center gap-1 text-white bg-blue-500 hover:bg-blue-600 text-sm px-2 py-1 rounded font-semibold leading-tight cursor-pointer active:scale-95 transition-transform duration-100 disabled:bg-gray-400 disabled:cursor-not-allowed"
                            onClick={() => {setRefreshTemp(!refreshTemp)}}
                            >
                            Refresh
                        </button>

                        <button
                            className="flex items-center gap-1 text-white bg-red-500 hover:bg-red-600 text-sm px-2 py-1 rounded font-semibold leading-tight cursor-pointer active:scale-95 transition-transform duration-100 disabled:bg-gray-400 disabled:cursor-not-allowed"
                            onClick={() => {setLines([])}}
                            >
                            Clear
                        </button>

                    </div>

                </div>
            </div>
        );
    }