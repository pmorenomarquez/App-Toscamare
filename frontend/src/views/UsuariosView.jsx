import { useState, useContext, useEffect, useRef, useMemo } from "react";
import { AppContext } from "@/context/AppContext";
import { ROLE_META } from "@/config/constants";
import { formatDate } from "@/utils/helpers";
import { SVG, Btn, Badge, Modal, Input, Select } from "@/components/ui";
import * as api from "@/utils/api";

// --- Componente UserActions y MenuBtn se mantienen igual que antes ---
const UserActions = ({ u, onAction, isSelf, onMenuToggle }) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  useEffect(() => {
    const close = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsOpen(false);
        setTimeout(() => onMenuToggle(false), 300);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [onMenuToggle]);

  return (
    <div ref={menuRef} style={{ position: "relative" }}>
      <button
        onClick={() => {
          const next = !isOpen;
          setIsOpen(next);
          onMenuToggle(next);
        }}
        className="btn-dots"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="1" />
          <circle cx="12" cy="5" r="1" />
          <circle cx="12" cy="19" r="1" />
        </svg>
      </button>
      {isOpen && (
        <div
          className="anim-scale"
          style={{
            position: "absolute",
            right: 0,
            bottom: "calc(100% + 10px)",
            zIndex: 10000,
            background: "var(--bg-3)",
            border: "1px solid var(--border-3)",
            borderRadius: "var(--r2)",
            width: 195,
            boxShadow: "0 -10px 40px rgba(0,0,0,0.8)",
            padding: 6,
          }}
        >
          <MenuBtn
            icon="user"
            label="Editar nombre"
            onClick={() => {
              onAction("edit-name", u);
              setIsOpen(false);
            }}
          />
          <MenuBtn
            icon="mail"
            label="Cambiar email"
            onClick={() => {
              onAction("edit-email", u);
              setIsOpen(false);
            }}
          />
          <MenuBtn
            icon="shield"
            label="Cambiar rol"
            onClick={() => {
              onAction("edit-role", u);
              setIsOpen(false);
            }}
          />
          {!isSelf && (
            <>
              <div
                style={{
                  height: 1,
                  background: "var(--border-1)",
                  margin: "4px 8px",
                }}
              />
              <MenuBtn
                icon="trash"
                label="Eliminar"
                color="var(--danger)"
                onClick={() => {
                  onAction("delete", u);
                  setIsOpen(false);
                }}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
};

const MenuBtn = ({ icon, label, onClick, color = "var(--text-2)" }) => (
  <button
    onClick={onClick}
    className="menu-item"
    style={{
      width: "100%",
      padding: "10px 12px",
      display: "flex",
      alignItems: "center",
      gap: 12,
      background: "none",
      border: "none",
      borderRadius: "var(--r1)",
      cursor: "pointer",
      color,
      fontSize: 13,
    }}
  >
    <SVG name={icon} size={15} color={color} />
    <span style={{ flex: 1, textAlign: "left" }}>{label}</span>
  </button>
);

export default function UsuariosView() {
  const { usuarios, showToast, session, loadUsuarios } = useContext(AppContext);
  const [showCreate, setShowCreate] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState(null);

  // --- ESTADOS DE EDICIÓN (NUEVOS) ---
  const [editingUser, setEditingUser] = useState(null);
  const [editMode, setEditMode] = useState(null);
  const [editValue, setEditValue] = useState("");

  // --- ESTADOS DE FILTRADO Y BUSQUEDA ---
  const [search, setSearch] = useState("");
  const [selectedRoles, setSelectedRoles] = useState([]);
  const [sortBy, setSortBy] = useState("name-asc"); // "name-asc", "name-desc", "role"

  const [form, setForm] = useState({ nombre: "", email: "", rol: "almacen" });

  useEffect(() => {
    loadUsuarios();
  }, [loadUsuarios]);

  // --- LÓGICA DE PROCESAMIENTO DE DATOS ---
  const processedUsers = useMemo(() => {
    let result = [...usuarios];

    if (search) {
      const s = search.toLowerCase();
      result = result.filter(
        (u) =>
          u.nombre.toLowerCase().includes(s) ||
          u.email.toLowerCase().includes(s),
      );
    }

    if (selectedRoles.length > 0) {
      result = result.filter((u) => selectedRoles.includes(u.rol));
    }

    result.sort((a, b) => {
      if (sortBy === "name-asc") return a.nombre.localeCompare(b.nombre);
      if (sortBy === "name-desc") return b.nombre.localeCompare(a.nombre);
      if (sortBy === "role") return a.rol.localeCompare(b.rol);
      return 0;
    });

    return result;
  }, [usuarios, search, selectedRoles, sortBy]);

  const toggleFilter = (roleKey) => {
    setSelectedRoles((prev) =>
      prev.includes(roleKey)
        ? prev.filter((r) => r !== roleKey)
        : [...prev, roleKey],
    );
  };

  const createUser = async () => {
    if (!form.nombre || !form.email) return showToast("Faltan datos", "error");
    try {
      await api.createUsuario(form);
      showToast("Usuario creado");
      setShowCreate(false);
      setForm({ nombre: "", email: "", rol: "almacen" });
      loadUsuarios();
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  // --- NUEVAS FUNCIONES DE EDICIÓN ---
  const handleAction = async (type, user) => {
    if (type === "delete") {
      if (window.confirm(`¿Seguro que quieres eliminar a ${user.nombre}?`)) {
        try {
          await api.deleteUsuario(user.id); // Esta la conectaremos luego
          showToast("Usuario eliminado");
          loadUsuarios();
        } catch (e) {
          showToast(e.message, "error");
        }
      }
      return;
    }

    setEditingUser(user);
    setEditMode(type);
    if (type === "edit-name") setEditValue(user.nombre);
    if (type === "edit-email") setEditValue(user.email);
    if (type === "edit-role") setEditValue(user.rol);
  };

  const saveEdit = async () => {
    if (!editValue) return showToast("El campo no puede estar vacío", "error");
    try {
      let data = {};
      if (editMode === "edit-name") data.nombre = editValue;
      if (editMode === "edit-email") data.email = editValue;
      if (editMode === "edit-role") data.rol = editValue;

      await api.updateUsuario(editingUser.id, data);
      showToast("Actualizado correctamente");
      setEditingUser(null);
      loadUsuarios();
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  return (
    <div
      style={{
        padding: "40px 40px 80px 40px",
        maxWidth: 1400,
        margin: "0 auto",
      }}
    >
      {/* HEADER PRINCIPAL */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 30,
        }}
      >
        <div>
          <h1 style={{ fontSize: 32, fontWeight: 700, color: "var(--text-1)" }}>
            Usuarios
          </h1>
          <p style={{ color: "var(--text-3)", fontSize: 15 }}>
            Gestión de accesos y permisos del equipo
          </p>
        </div>
        <Btn variant="primary" icon="plus" onClick={() => setShowCreate(true)}>
          Nuevo Usuario
        </Btn>
      </div>

      {/* BARRA DE HERRAMIENTAS */}
      <div
        style={{
          background: "var(--bg-2)",
          padding: "20px",
          borderRadius: "var(--r3)",
          border: "1px solid var(--border-1)",
          marginBottom: 30,
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 15,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <div style={{ flex: 1, minWidth: 280, position: "relative" }}>
            <div
              style={{
                position: "absolute",
                left: 12,
                top: "50%",
                transform: "translateY(-50%)",
                opacity: 0.5,
              }}
            >
              <SVG name="search" size={18} />
            </div>
            <input
              type="text"
              placeholder="Buscar por nombre o email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="custom-search-input"
            />
          </div>

          <div style={{ minWidth: 200 }}>
            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              options={[
                { value: "name-asc", label: "Nombre (A - Z)" },
                { value: "name-desc", label: "Nombre (Z - A)" },
                { value: "role", label: "Agrupar por Rol" },
              ]}
            />
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            alignItems: "center",
            borderTop: "1px solid var(--border-1)",
            paddingTop: 15,
          }}
        >
          <span
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "var(--text-4)",
              marginRight: 10,
            }}
          >
            FILTRAR POR:
          </span>
          {Object.entries(ROLE_META).map(([key, meta]) => (
            <button
              key={key}
              onClick={() => toggleFilter(key)}
              className={`filter-pill ${selectedRoles.includes(key) ? "active" : ""}`}
              style={{ "--pill-color": meta.color }}
            >
              <span className="dot" />
              {meta.label}
            </button>
          ))}
          {selectedRoles.length > 0 && (
            <button onClick={() => setSelectedRoles([])} className="clear-btn">
              Limpiar
            </button>
          )}
        </div>
      </div>

      {/* GRID DE USUARIOS */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
          gap: 20,
        }}
      >
        {processedUsers.map((u, i) => {
          const meta = ROLE_META[u.rol];
          return (
            <div
              key={u.id}
              className="user-card"
              style={{
                background: "var(--bg-2)",
                border: "1px solid var(--border-1)",
                borderRadius: "var(--r3)",
                padding: 24,
                position: "relative",
                zIndex: activeMenuId === u.id ? 9999 : 1,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                }}
              >
                <div style={{ display: "flex", gap: 16 }}>
                  <div
                    style={{
                      width: 52,
                      height: 52,
                      borderRadius: "var(--r2)",
                      background: meta.color + "15",
                      border: `1px solid ${meta.color}30`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <SVG name="user" size={24} color={meta.color} />
                  </div>
                  <div>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: 17,
                        color: "var(--text-1)",
                      }}
                    >
                      {u.nombre}
                    </div>
                    <div
                      style={{
                        fontSize: 13,
                        color: "var(--text-3)",
                        marginTop: 2,
                      }}
                    >
                      {u.email}
                    </div>
                  </div>
                </div>
                <UserActions
                  u={u}
                  isSelf={u.id === session?.user?.id}
                  onAction={handleAction}
                  onMenuToggle={(open) => setActiveMenuId(open ? u.id : null)}
                />
              </div>
              <div
                style={{
                  marginTop: 24,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Badge color={meta.color}>{meta.label}</Badge>
                <div style={{ fontSize: 12, color: "var(--text-4)" }}>
                  {formatDate(u.created_at)}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* MODAL CREAR (Tuyo original) */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Nuevo Usuario"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <Input
            label="NOMBRE"
            placeholder="Nombre completo"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
          />
          <Input
            label="EMAIL"
            placeholder="email@empresa.com"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <div className="custom-select-wrapper">
            <label
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: "var(--text-3)",
                marginBottom: 8,
                display: "block",
              }}
            >
              ROL DE ACCESO
            </label>
            <Select
              value={form.rol}
              onChange={(e) => setForm({ ...form, rol: e.target.value })}
              options={Object.entries(ROLE_META).map(([k, v]) => ({
                value: k,
                label: v.label,
              }))}
            />
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 12,
              marginTop: 10,
            }}
          >
            <Btn variant="secondary" onClick={() => setShowCreate(false)}>
              Cancelar
            </Btn>
            <Btn variant="primary" onClick={createUser}>
              Crear Usuario
            </Btn>
          </div>
        </div>
      </Modal>

      {/* MODAL EDITAR DINÁMICO (Nuevo) */}
      <Modal
        open={!!editingUser}
        onClose={() => setEditingUser(null)}
        title={
          editMode === "edit-name"
            ? "Editar Nombre"
            : editMode === "edit-email"
              ? "Cambiar Email"
              : "Cambiar Rol"
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {editMode === "edit-role" ? (
            <div className="custom-select-wrapper">
              <label
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: "var(--text-3)",
                  marginBottom: 8,
                  display: "block",
                }}
              >
                NUEVO ROL
              </label>
              <Select
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                options={Object.entries(ROLE_META).map(([k, v]) => ({
                  value: k,
                  label: v.label,
                }))}
              />
            </div>
          ) : (
            <Input
              label={
                editMode === "edit-name" ? "NOMBRE COMPLETO" : "NUEVO EMAIL"
              }
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
            />
          )}

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 12,
              marginTop: 10,
            }}
          >
            <Btn variant="secondary" onClick={() => setEditingUser(null)}>
              Cancelar
            </Btn>
            <Btn variant="primary" onClick={saveEdit}>
              Guardar Cambios
            </Btn>
          </div>
        </div>
      </Modal>

      <style jsx global>{`
        .user-card {
          transition: all 0.2s ease;
        }
        .user-card:hover {
          border-color: var(--border-3);
          transform: translateY(-4px);
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        .menu-item:hover {
          background: var(--bg-4) !important;
          color: var(--text-1) !important;
        }
        .custom-search-input {
          width: 100%;
          background: var(--bg-3);
          border: 1px solid var(--border-2);
          padding: 12px 12px 12px 40px;
          border-radius: var(--r2);
          color: var(--text-1);
          font-size: 14px;
          outline: none;
          transition: border 0.2s;
        }
        .custom-search-input:focus {
          border-color: var(--accent);
        }
        .filter-pill {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 14px;
          border-radius: 100px;
          background: var(--bg-3);
          border: 1px solid var(--border-2);
          color: var(--text-2);
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: 0.2s;
        }
        .filter-pill.active {
          background: var(--pill-color);
          border-color: var(--pill-color);
          color: white;
        }
        .filter-pill .dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--pill-color);
        }
        .filter-pill.active .dot {
          background: white;
        }
        .clear-btn {
          background: none;
          border: none;
          color: var(--danger);
          font-size: 11px;
          cursor: pointer;
          font-weight: 600;
          text-transform: uppercase;
        }
        .btn-dots {
          background: none;
          border: none;
          cursor: pointer;
          padding: 6px;
          border-radius: var(--r1);
          color: var(--text-3);
          display: flex;
        }
        .btn-dots:hover {
          background: var(--bg-4);
          color: var(--text-1);
        }
      `}</style>
    </div>
  );
}
