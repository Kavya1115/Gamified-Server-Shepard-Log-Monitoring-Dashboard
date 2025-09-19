/* Frontend React code as provided above */
import React, { useEffect, useRef, useState } from "react";
import { ReactP5Wrapper } from "@p5-wrapper/react";

const WS_URL = (host => `ws://${host}/ws`)(location.hostname + (location.port ? ":" + 8000 : "")); // assumes backend on 8000

function Sketch(props) {
  const { events, onClickSheep } = props;

  let sheepList = []; // will be replaced each frame from events

  return (p) => {
    // state inside p5 instance
    let sheep = [];

    p.setup = () => {
      p.createCanvas(p.windowWidth, p.windowHeight - 40);
      p.frameRate(30);
    };

    p.windowResized = () => {
      p.resizeCanvas(p.windowWidth, p.windowHeight - 40);
    };

    function spawnSheepFromEvents() {
      // create local sheep array from events
      sheep = events.map((e, i) => {
        // random position or persist some positions based on id hash
        const hash = [...e.id].reduce((a,c)=>a + c.charCodeAt(0),0);
        const x = (hash * 37) % p.width;
        const y = ((hash * 97) % (p.height - 60)) + 30;
        const size = 24 + (e.status % 10);
        let color;
        if (e.acknowledged) color = [150,150,150];
        else if (e.level === "error") color = [220, 80, 80];
        else if (e.level === "warning") color = [220, 180, 60];
        else color = [80, 200, 120];
        return { id: e.id, x, y, vx: (hash % 3)-1, vy: (hash % 5)-2, size, color, raw: e.raw, level: e.level, acknowledged: e.acknowledged };
      });
    }

    p.draw = () => {
      p.background(20);
      // small field
      p.fill(30);
      p.noStroke();
      p.rect(0, 0, p.width, p.height);

      spawnSheepFromEvents();

      // animate and draw sheep
      sheep.forEach(s => {
        // wandering
        s.x += (Math.sin(p.frameCount * 0.01 + s.x) * 0.5) + s.vx * 0.5;
        s.y += Math.cos(p.frameCount * 0.008 + s.y) * 0.3 + s.vy * 0.2;
        // bounds
        s.x = p.constrain(s.x, s.size/2, p.width - s.size/2);
        s.y = p.constrain(s.y, s.size/2, p.height - s.size/2);

        p.push();
        p.translate(s.x, s.y);
        p.noStroke();
        p.fill(...s.color);
        // draw body
        p.ellipse(0, 0, s.size*1.6, s.size);
        // head
        p.fill(40);
        p.ellipse(s.size*0.6, -s.size*0.1, s.size*0.6, s.size*0.5);
        p.pop();

        // make "error" sheep fall occasionally (shake)
        if (s.level === "error" && !s.acknowledged && Math.abs(Math.sin(p.frameCount*0.1 + s.x)) > 0.98) {
          p.push();
          p.translate(s.x, s.y + 6);
          p.fill(120, 40, 40, 120);
          p.ellipse(0, 0, s.size*1.2, s.size*0.6);
          p.pop();
        }
      });

      // store for click detection
      sheepList = sheep;
    };

    // register click handler to call onClickSheep with id
    p.mousePressed = () => {
      for (let s of sheepList) {
        const d = Math.hypot(p.mouseX - s.x, p.mouseY - s.y);
        if (d < s.size) {
          if (onClickSheep) onClickSheep(s);
          break;
        }
      }
    };

    // expose a method so parent can request redraw or update, optional
    p.myCustomRedrawAccordingToNewPropsHandler = (newProps) => {
      // events are read from outer props each draw
    };
  };
}

export default function App() {
  const [events, setEvents] = useState([]); // list of structured events
  const wsRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const backendHost = `${location.hostname}:8000`;

  useEffect(() => {
    // fetch current events initially
    fetch(`http://${backendHost}/events`)
      .then(r => r.json())
      .then(j => setEvents(j.events || []))
      .catch(() => {});

    // open WebSocket
    const ws = new WebSocket(`ws://${backendHost}/ws`);
    ws.onopen = () => console.log("ws open");
    ws.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        if (payload.type === "init") {
          setEvents(payload.events || []);
        } else if (payload.type === "log_event") {
          setEvents(prev => [payload.event, ...prev].slice(0, 200));
        } else if (payload.type === "ack") {
          setEvents(prev => prev.map(e => e.id === payload.id ? {...e, acknowledged: true} : e));
        }
      } catch (e) { console.error(e); }
    };
    ws.onclose = () => console.log("ws closed");
    wsRef.current = ws;
    return () => {
      ws.close();
    };
  }, []);

  function onClickSheep(s) {
    setSelected(s);
  }

  async function acknowledge() {
    if (!selected) return;
    await fetch(`http://${backendHost}/acknowledge/${selected.id}`, { method: "POST" });
    setEvents(prev => prev.map(e => e.id === selected.id ? {...e, acknowledged: true} : e));
    setSelected(prev => prev ? {...prev, acknowledged: true} : prev);
  }

  return (
    <div>
      <div style={{height: 40, background: "#111", color: "#fff", padding: 8, display: "flex", alignItems: "center", gap: 12}}>
        <div style={{fontWeight: 700}}>Server Shepherd — Live</div>
        <div style={{marginLeft: "auto"}}>Events: {events.length}</div>
      </div>

      <ReactP5Wrapper sketch={Sketch} events={events} onClickSheep={onClickSheep} />

      {selected && (
        <div style={{
          position: "fixed",
          right: 20,
          top: 60,
          width: 360,
          background: "#fff",
          boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
          padding: 12,
          zIndex: 100
        }}>
          <h3 style={{marginTop:0}}>Event</h3>
          <div><strong>Status:</strong> {selected.status}</div>
          <div style={{marginTop:8, whiteSpace:"pre-wrap", fontFamily:"monospace"}}>{selected.raw}</div>
          <div style={{marginTop:12, display:"flex", gap:8}}>
            <button onClick={() => setSelected(null)}>Close</button>
            {!selected.acknowledged && <button onClick={acknowledge}>Acknowledge</button>}
          </div>
        </div>
      )}
    </div>
  );
}