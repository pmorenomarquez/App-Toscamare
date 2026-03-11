import { useState, useRef, useContext } from "react";
import { AppContext } from "@/context/AppContext";
import { Modal, Btn } from "@/components/ui";
import SignatureCanvas from "react-signature-canvas";
import * as api from "@/utils/api";

export default function FirmaModal({ open, onClose, pedido }) {
  const { showToast, loadPedidos } = useContext(AppContext);
  const sigRef = useRef(null);
  const [saving, setSaving] = useState(false);

  const handleClear = () => sigRef.current?.clear();

  const handleSave = async () => {
    if (!sigRef.current || sigRef.current.isEmpty()) {
      showToast("El cliente debe firmar antes de confirmar", "error");
      return;
    }

    setSaving(true);
    try {
      // Exportar firma como PNG (necesario para transparencia en el PDF)
      const dataURL = sigRef.current.toDataURL("image/png");

      await api.firmarPedido(pedido.id, dataURL);
      showToast("Firma registrada y PDF actualizado");
      await loadPedidos();
      onClose();
    } catch (e) {
      showToast(e.message || "Error al guardar firma", "error");
    } finally {
      setSaving(false);
    }
  };

  if (!pedido) return null;

  return (
    <Modal open={open} onClose={onClose} title={"Firma del cliente — " + pedido.codigo}>
      <p style={{ fontSize: 13, color: "var(--text-3)", marginBottom: 14 }}>
        El cliente debe firmar en el recuadro para confirmar la recepcion del pedido.
      </p>

      <div
        style={{
          border: "2px dashed var(--border-2)",
          borderRadius: "var(--r2)",
          background: "#fff",
          marginBottom: 16,
        }}
      >
        <SignatureCanvas
          ref={sigRef}
          penColor="#111"
          canvasProps={{
            width: 476,
            height: 200,
            style: { width: "100%", height: 200, display: "block" },
          }}
        />
      </div>

      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <Btn variant="ghost" onClick={handleClear} disabled={saving}>
          Borrar firma
        </Btn>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="outline" onClick={onClose} disabled={saving}>
            Cancelar
          </Btn>
          <Btn variant="primary" icon="check" onClick={handleSave} disabled={saving}>
            {saving ? "Guardando..." : "Confirmar entrega"}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}
