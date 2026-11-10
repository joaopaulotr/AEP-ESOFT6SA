import { useTheme } from '../hooks/useTheme'


export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      style={{
        display: 'inline-grid',
        placeItems: 'center',
        width: 'var(--touch-target)',
        height: 'var(--touch-target)',
        borderRadius: 'var(--radius-full)',
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface-2)',
        color: 'var(--color-text)',
        cursor: 'pointer',
      }}
      onClick={toggleTheme}
      aria-label={isDark ? 'Ativar tema claro' : 'Ativar tema escuro'}
      aria-pressed={isDark}
      title={isDark ? 'Tema claro' : 'Tema escuro'}
    >
      {isDark ? (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  )
}
