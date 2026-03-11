import { useState, useContext, useEffect, useRef, useMemo } from "react";
import { AppContext } from "@/context/AppContext";
import { ROLE_META } from "@/config/constants";
import { formatDate } from "@/utils/helpers";
import { SVG, Btn, Badge, Modal, Input, Select } from "@/components/ui";
import * as api from "@/utils/api";
import UserCardSkeleton from "@/components/userCard/UserCardSkeleton";

import "./UsuariosView.css";

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
    <div ref={menuRef} className="user-actions-wrapper">
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
        <div className="anim-scale dropdown-menu">
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
              <div className="dropdown-divider" />
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
  <button onClick={onClick} className="menu-item" style={{ color }}>
    <SVG name={icon} size={15} color={color} />
    <span className="menu-btn-label">{label}</span>
  </button>
);

const UserCard = ({
  user,
  activeMenuId,
  isSelf,
  onAction,
  onMenuToggle,
  index,
}) => {
  const meta = ROLE_META[user.rol];

  return (
    <div
      className="user-card"
      style={{
        zIndex: activeMenuId === user.id ? 9999 : 1,
        animationDelay: `${index * 0.15}s`, // <-- Animación en cascada
      }}
    >
      <div className="card-header">
        <div className="card-user-info">
          <div
            className="card-avatar"
            style={{
              background: meta.color + "15",
              border: `1px solid ${meta.color}30`,
            }}
          >
            <SVG name="user" size={24} color={meta.color} />
          </div>
          <div>
            <div className="card-user-name">{user.nombre}</div>
            <div className="card-user-email">{user.email}</div>
          </div>
        </div>

        <UserActions
          u={user}
          isSelf={isSelf}
          onAction={onAction}
          onMenuToggle={onMenuToggle}
        />
      </div>

      <div className="card-footer">
        <Badge color={meta.color}>{meta.label}</Badge>
        <div className="card-date">{formatDate(user.created_at)}</div>
      </div>
    </div>
  );
};

export default function UsuariosView() {
  const { usuarios, showToast, session, loadUsuarios } = useContext(AppContext);

  const [showCreate, setShowCreate] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState(null);

  // --- ESTADO LOCAL PARA EL SKELETON ---
  const [cargandoDatos, setCargandoDatos] = useState(true);

  const [editingUser, setEditingUser] = useState(null);
  const [editMode, setEditMode] = useState(null);
  const [editValue, setEditValue] = useState("");

  const [search, setSearch] = useState("");
  const [selectedRoles, setSelectedRoles] = useState([]);
  const [sortBy, setSortBy] = useState("name-asc");

  const [form, setForm] = useState({ nombre: "", email: "", rol: "almacen" });

  // --- EFECTO DE CARGA ---
  useEffect(() => {
    const hacerCarga = async () => {
      setCargandoDatos(true);
      try {
        await loadUsuarios();
      } catch (error) {
        console.error("Error cargando usuarios", error);
      } finally {
        setCargandoDatos(false);
      }
    };

    hacerCarga();
  }, [loadUsuarios]);

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

  const handleAction = async (type, user) => {
    if (type === "delete") {
      if (window.confirm(`¿Seguro que quieres eliminar a ${user.nombre}?`)) {
        try {
          await api.deleteUsuario(user.id);
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
    <div className="view-wrapper">
      {/* HEADER PRINCIPAL */}
      <div className="view-header">
        <div>
          <h1 className="view-title">Usuarios</h1>
          <p className="view-subtitle">
            Gestión de accesos y permisos del equipo
          </p>
        </div>
        <Btn variant="primary" icon="plus" onClick={() => setShowCreate(true)}>
          Nuevo Usuario
        </Btn>
      </div>

      {/* BARRA DE HERRAMIENTAS */}
      <div className="toolbar">
        <div className="toolbar-top">
          <div className="search-wrapper">
            <div className="search-icon">
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

          <div className="sort-wrapper">
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

        <div className="toolbar-bottom">
          <span className="filter-label">FILTRAR POR:</span>
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
      <div className="users-grid">
        {cargandoDatos ? (
          // Pasamos el index al skeleton para la animación en cascada
          Array.from({ length: 9 }).map((_, index) => (
            <UserCardSkeleton key={index} index={index} />
          ))
        ) : processedUsers.length > 0 ? (
          // Pasamos el index a la tarjeta real
          processedUsers.map((u, index) => (
            <UserCard
              key={`${u.id}-${selectedRoles.join("-")}`}
              user={u}
              index={index}
              activeMenuId={activeMenuId}
              isSelf={u.id === session?.user?.id}
              onAction={handleAction}
              onMenuToggle={(open) => setActiveMenuId(open ? u.id : null)}
            />
          ))
        ) : (
          // Mensaje de estado vacío corregido visualmente
          <div
            style={{
              gridColumn: "1 / -1",
              textAlign: "center",
              color: "var(--text-3)",
              padding: "40px 0",
            }}
          >
            No se encontraron usuarios.
          </div>
        )}
      </div>

      {/* MODAL CREAR */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Nuevo Usuario"
      >
        <div className="modal-content">
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
            <label className="modal-label">ROL DE ACCESO</label>
            <Select
              value={form.rol}
              onChange={(e) => setForm({ ...form, rol: e.target.value })}
              options={Object.entries(ROLE_META).map(([k, v]) => ({
                value: k,
                label: v.label,
              }))}
            />
          </div>
          <div className="modal-actions">
            <Btn variant="secondary" onClick={() => setShowCreate(false)}>
              Cancelar
            </Btn>
            <Btn variant="primary" onClick={createUser}>
              Crear Usuario
            </Btn>
          </div>
        </div>
      </Modal>

      {/* MODAL EDITAR DINÁMICO */}
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
        <div className="modal-content">
          {editMode === "edit-role" ? (
            <div className="custom-select-wrapper">
              <label className="modal-label">NUEVO ROL</label>
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

          <div className="modal-actions">
            <Btn variant="secondary" onClick={() => setEditingUser(null)}>
              Cancelar
            </Btn>
            <Btn variant="primary" onClick={saveEdit}>
              Guardar Cambios
            </Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
