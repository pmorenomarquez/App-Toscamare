import { useState, useRef, useEffect } from "react";
import { Modal, Btn, SVG } from "@/components/ui";
import SignatureCanvas from "react-signature-canvas";
import * as api from "@/utils/api";

export default function SignatureModal({ open, onClose, pedido }) {
  const sigRef = useRef(null);
  const wrapperRef = useRef(null);
  const canvasContainerRef = useRef(null);
  const lastDataRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [penWidths, setPenWidths] = useState({ min: 0.5, max: 1 });
  const [bgUrl, setBgUrl] = useState(null);
  const [loadingPdf, setLoadingPdf] = useState(true);

  useEffect(() => {
    if (open && pedido) {
      lastDataRef.current = localStorage.getItem('firma_' + pedido.id) || null;
    }
  }, [open, pedido]);

  // Load PDF background
  useEffect(() => {
    if (open && pedido) {
      setLoadingPdf(true);
      api.getPDFPreviewUrl(pedido.id)
        .then(url => setBgUrl(url))
        .catch(err => console.error("Error loading PDF preview:", err))
        .finally(() => setLoadingPdf(false));
    } else {
      setBgUrl(null);
    }
  }, [open, pedido]);

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
      
      // Update pen thickness proportionally
      const scale = w / 350;
      setPenWidths({ min: Math.max(0.2, 0.5 * scale), max: Math.max(0.5, 1 * scale) });
      
      const ratio = Math.max(window.devicePixelRatio || 1, 1);
      const targetW = w * ratio;
      const targetH = h * ratio;
      
      if (canvas.width === targetW && canvas.height === targetH) return;
      
      const currentData = sigRef.current.isEmpty() ? null : sigRef.current.toDataURL();
      if (currentData) {
        lastDataRef.current = currentData;
      }
      
      canvas.width = targetW;
      canvas.height = targetH;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      canvas.getContext("2d").scale(ratio, ratio);
      
      sigRef.current.clear();
      
      if (lastDataRef.current && lastDataRef.current !== "data:,") {
        setTimeout(() => {
          if (sigRef.current) sigRef.current.fromDataURL(lastDataRef.current);
        }, 30);
      }
    };

    const observer = new ResizeObserver(() => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resizeCanvas, 50);
    });
    
    if (canvasContainerRef.current) {
      // Small delay initially to let the img dictate the container size
      setTimeout(resizeCanvas, 50);
      observer.observe(canvasContainerRef.current);
    }
    
    return () => {
      clearTimeout(resizeTimer);
      observer.disconnect();
    };
  }, [open, bgUrl]);

  const handleClear = () => {
    sigRef.current?.clear();
    lastDataRef.current = null;
  };

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
              Firme directamente sobre el albarán en la vista previa.
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
              position: 'relative',
              borderRadius: "var(--r2)",
              background: "var(--bg-2)",
              overflow: 'hidden',
              maxHeight: isFullscreen ? 'calc(100vh - 120px)' : '50vh',
              maxWidth: isFullscreen ? 'calc(100vh - 120px)' : '100%',
              display: 'inline-block', // shrinkwrap to img
              boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
              border: "1px solid var(--border-2)"
            }}
          >
            {loadingPdf && (
              <div style={{ width: 300, height: 400, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <p style={{ fontSize: 13, color: "var(--text-4)" }}>Cargando factura...</p>
              </div>
            )}
            {!loadingPdf && bgUrl && (
              <img 
                src={bgUrl} 
                alt="Documento" 
                style={{ 
                  display: "block", 
                  maxWidth: "100%", 
                  maxHeight: isFullscreen ? 'calc(100vh - 120px)' : '50vh', 
                  objectFit: "contain",
                  pointerEvents: "none",
                  userSelect: "none"
                }} 
              />
            )}
            {!loadingPdf && !bgUrl && (
              <div style={{ width: 300, height: 400, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <p style={{ fontSize: 13, color: "var(--text-4)" }}>No se pudo cargar el PDF</p>
              </div>
            )}

            {bgUrl && (
              <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, zIndex: 10 }}>
                <SignatureCanvas
                  ref={sigRef}
                  penColor="#000" // Negro
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
            )}
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
