import { useState, useContext, useRef } from 'react';
import { AppContext } from '@/context/AppContext';
import { Modal, Btn, Input, SVG } from '@/components/ui';
import * as api from '@/utils/api';

export default function PedidoFormModal({ open, onClose }) {
  const { showToast, loadPedidos } = useContext(AppContext);
  const [clienteNombre, setClienteNombre] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);

  const handleClose = () => {
    setClienteNombre('');
    setPdfFile(null);
    if (fileRef.current) fileRef.current.value = '';
    onClose();
  };

  const handleSave = async () => {
    if (!clienteNombre.trim()) { showToast('El nombre del cliente es obligatorio', 'error'); return; }
    if (!pdfFile) { showToast('El PDF del pedido es obligatorio', 'error'); return; }

    setSaving(true);
    showToast('Subiendo PDF y procesando OCR... esto puede tardar', 'info');
    try {
      await api.createPedido(clienteNombre.trim(), pdfFile);
      showToast('Pedido creado con productos extraídos del PDF');
      await loadPedidos();
      handleClose();
    } catch (e) {
      showToast('Error: ' + e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={handleClose} title="Nuevo Pedido">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
        <Input
          label="CLIENTE *"
          placeholder="Nombre del cliente"
          value={clienteNombre}
          onChange={e => setClienteNombre(e.target.value)}
        />

        {/* PDF Upload */}
        <div>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '.04em', display: 'block', marginBottom: 6 }}>
            PDF del pedido *
          </span>
          <div style={{
            padding: 20, borderRadius: 'var(--r2)', border: '2px dashed var(--border-2)',
            background: 'var(--bg-1)', textAlign: 'center', cursor: 'pointer',
            transition: '.15s var(--ease)',
          }}
            onClick={() => fileRef.current?.click()}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-2)'}>
            <input ref={fileRef} type="file" accept=".pdf" style={{ display: 'none' }}
              onChange={e => setPdfFile(e.target.files[0] || null)} />
            {saving ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '10px 0' }}>
                <div className="anim-spin" style={{ display: 'flex', marginBottom: 16 }}>
                  <SVG name="loader" size={32} color="var(--accent)" />
                </div>
                <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-1)' }}>Procesando documento...</p>
                <p style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 4 }}>La IA está extrayendo los productos del PDF. Por favor, espera.</p>
              </div>
            ) : pdfFile ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                <SVG name="file" size={18} color="var(--accent)" />
                <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--accent)' }}>{pdfFile.name}</span>
                <Btn variant="ghost" size="sm" icon="x" onClick={(e) => { e.stopPropagation(); setPdfFile(null); if (fileRef.current) fileRef.current.value = ''; }} />
              </div>
            ) : (
              <div>
                <SVG name="upload" size={24} color="var(--text-4)" />
                <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 8 }}>
                  Haz clic para seleccionar el PDF del albarán
                </p>
                <p style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 4 }}>
                  Los productos se extraerán automáticamente por OCR
                </p>
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
          <Btn variant="secondary" onClick={handleClose} disabled={saving}>Cancelar</Btn>
          <Btn variant="primary" icon="plus" disabled={saving} onClick={handleSave}>
            {saving ? 'Procesando PDF...' : 'Crear Pedido'}
          </Btn>
        </div>
      </div>
    </Modal>
  );
}
