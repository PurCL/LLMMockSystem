import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
    Layout,
    Files,
    Upload as UploadIcon,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';
import logo from '../assets/logo.svg';

export const Sidebar = () => {
    const [isCollapsed, setIsCollapsed] = useState(false);

    const toggleSidebar = () => setIsCollapsed(!isCollapsed);

    const navItems = [
        { to: '/documents', icon: <Files size={20} />, label: 'Documents' },
        { to: '/upload', icon: <UploadIcon size={20} />, label: 'Upload' },
    ];

    return (
        <aside
            className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}
            style={{
                width: isCollapsed ? '64px' : '240px',
                backgroundColor: 'var(--sidebar-bg)',
                borderRight: '1px solid var(--border-color)',
                height: '100vh',
                transition: 'width 0.3s ease',
                display: 'flex',
                flexDirection: 'column',
                position: 'sticky',
                top: 0,
                zIndex: 10,
                boxShadow: isCollapsed ? 'none' : 'var(--shadow-sm)',
                overflowX: 'hidden'
            }}
        >
            {/* Brand Header */}
            <div style={{
                padding: isCollapsed ? '1rem 0' : '1.25rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: isCollapsed ? 'center' : 'space-between',
                height: '4rem',
                borderBottom: '1px solid var(--border-color)',
                width: '100%'
            }}>
                <div
                    onClick={() => window.location.href = '/'}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        overflow: 'hidden',
                        justifyContent: isCollapsed ? 'center' : 'flex-start',
                        width: isCollapsed ? '100%' : 'auto',
                        cursor: 'pointer'
                    }}>
                    <img
                        src={logo}
                        alt="DocuServe"
                        style={{
                            width: '40px',
                            height: '40px',
                            objectFit: 'contain',
                            flexShrink: 0
                        }}
                    />
                    {!isCollapsed && (
                        <span style={{
                            fontWeight: 700,
                            fontSize: '1.125rem',
                            color: 'var(--text-primary)',
                            whiteSpace: 'nowrap'
                        }}>
                            DocuServe
                        </span>
                    )}
                </div>

                {!isCollapsed && (
                    <button
                        onClick={toggleSidebar}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                        }}
                    >
                        <ChevronLeft size={16} />
                    </button>
                )}
            </div>

            {/* Navigation Links */}
            <nav style={{ flex: 1, padding: '1rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {navItems.map((item) => (
                    <NavLink
                        key={item.to}
                        to={item.to}
                        className={({ isActive }) =>
                            `nav-item ${isActive ? 'active' : ''}`
                        }
                        style={({ isActive }) => ({
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            padding: isCollapsed ? '0.75rem 0' : '0.75rem',
                            borderRadius: 'var(--radius)',
                            color: isActive ? 'var(--primary)' : 'var(--text-secondary)',
                            backgroundColor: isActive ? '#eff6ff' : 'transparent',
                            textDecoration: 'none',
                            transition: 'all 0.2s',
                            fontWeight: isActive ? 600 : 500,
                            justifyContent: isCollapsed ? 'center' : 'flex-start',
                            width: '100%'
                        })}
                        title={isCollapsed ? item.label : ''}
                    >
                        {item.icon}
                        {!isCollapsed && (
                            <span style={{ fontSize: '0.9rem' }}>{item.label}</span>
                        )}
                    </NavLink>
                ))}
            </nav>

            {/* Collapse Button (Bottom) - Only show when collapsed to expand */}
            {isCollapsed && (
                <div style={{ padding: '1rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'center' }}>
                    <button
                        onClick={toggleSidebar}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                        }}
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>
            )}
        </aside>
    );
};
