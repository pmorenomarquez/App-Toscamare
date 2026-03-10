import { useState, useRef, useEffect } from "react";
import { Modal, Btn, SVG } from "@/components/ui";
import SignatureCanvas from "react-signature-canvas";

export default function SignatureModal({ open, onClose, pedido }) {
  const sigRef = useRef(null);
  const wrapperRef = useRef(null);
  const canvasContainerRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [penWidths, setPenWidths] = useState({ min: 2, max: 4 });

  // Handle Fullscreen events syncing with state
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  // Resize canvas so drawing tracks pointer accurately and pen width scales with container
  useEffect(() => {
    if (!open) return;
    
    let resizeTimer;
    const resizeCanvas = () => {
      if (!canvasContainerRef.current || !sigRef.current) return;
      const parent = canvasContainerRef.current;
      const canvas = sigRef.current.getCanvas();
      
      const w = parent.offsetWidth;
      const h = parent.offsetHeight;
      if (w === 0 || h === 0) return;
      
      // Update pen thickness proportionally (assume base width of 350px -> min 2, max 4)
      const scale = w / 350;
      setPenWidths({ min: Math.max(1, 2 * scale), max: Math.max(2, 4 * scale) });
      
      const ratio = Math.max(window.devicePixelRatio || 1, 1);
      const targetW = w * ratio;
      const targetH = h * ratio;
      
      if (canvas.width === targetW && canvas.height === targetH) return;
      
      const data = sigRef.current.isEmpty() ? null : sigRef.current.toDataURL();
      
      canvas.width = targetW;
      canvas.height = targetH;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      canvas.getContext("2d").scale(ratio, ratio);
      
      sigRef.current.clear();
      if (data && data !== "data:,") {
        setTimeout(() => {
          if (sigRef.current) sigRef.current.fromDataURL(data);
        }, 10);
      }
    };

    const observer = new ResizeObserver(() => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resizeCanvas, 50);
    });
    
    if (canvasContainerRef.current) {
      observer.observe(canvasContainerRef.current);
    }
    
    return () => {
      clearTimeout(resizeTimer);
      observer.disconnect();
    };
  }, [open]);

  // Restore signature initially if we have one
  useEffect(() => {
    if (open && pedido && sigRef.current) {
      const saved = localStorage.getItem('firma_' + pedido.id);
      if (saved) {
        setTimeout(() => {
          if (sigRef.current) sigRef.current.fromDataURL(saved);
        }, 100);
      } else {
        sigRef.current.clear();
      }
    }
  }, [open, pedido]);

  const handleClear = () => sigRef.current?.clear();

  const handleSaveLocal = () => {
    if (!sigRef.current || sigRef.current.isEmpty()) {
      onClose();
      return;
    }
    const dataURL = sigRef.current.toDataURL("image/png");
    localStorage.setItem('firma_' + pedido.id, dataURL);
    onClose();
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      wrapperRef.current?.requestFullscreen().catch(err => {
        console.error(`Error entering full-screen: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  if (!pedido) return null;

  return (
    <Modal open={open} onClose={onClose} title={"Firma - " + pedido.codigo}>
      <div 
        ref={wrapperRef} 
        style={{ 
          background: isFullscreen ? 'var(--bg-0)' : 'transparent',
          padding: isFullscreen ? '24px' : '0',
          display: 'flex', 
          flexDirection: 'column',
          height: isFullscreen ? '100vh' : 'auto',
          width: isFullscreen ? '100vw' : 'auto',
          boxSizing: 'border-box'
        }}
      >
        {isFullscreen && (
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: 18, fontWeight: 600 }}>Firma - {pedido.codigo}</h2>
            <Btn variant="ghost" icon="x" onClick={toggleFullscreen}>Cerrar completa</Btn>
          </div>
        )}

        {!isFullscreen && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
            <p style={{ fontSize: 13, color: "var(--text-3)" }}>
              Firme en el recuadro inferior.
            </p>
            <Btn variant="ghost" size="sm" icon="maximize" onClick={toggleFullscreen} title="Pantalla completa">
              Pantalla completa
            </Btn>
          </div>
        )}

        <div style={{ flexGrow: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 16 }}>
          <div
            ref={canvasContainerRef}
            style={{
              border: "2px dashed var(--border-2)",
              borderRadius: "var(--r2)",
              background: "#fff",
              overflow: 'hidden',
              width: "100%",
              aspectRatio: '1 / 1',
              maxHeight: isFullscreen ? 'calc(100vh - 120px)' : '50vh',
              maxWidth: isFullscreen ? 'calc(100vh - 120px)' : '100%'
            }}
          >
            <SignatureCanvas
              ref={sigRef}
              penColor="#111"
              minWidth={penWidths.min}
              maxWidth={penWidths.max}
              canvasProps={{
                className: "sigCanvas",
                style: { 
                  width: "100%", 
                  height: "100%", 
                  display: "block",
                  cursor: "crosshair"
                },
              }}
            />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: isFullscreen ? 'auto' : 0 }}>
          <Btn variant="ghost" onClick={handleClear}>
            Borrar firma
          </Btn>
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant="outline" onClick={onClose}>
              Cancelar
            </Btn>
            <Btn variant="primary" icon="check" onClick={handleSaveLocal}>
              Guardar temporalmente
            </Btn>
          </div>
        </div>
      </div>
    </Modal>
  );
}
