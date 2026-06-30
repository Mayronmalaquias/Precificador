import React, { useState } from 'react';

// Input de senha com olhinho pra mostrar/ocultar. Repassa todas as props pro <input>.
export default function PasswordInput({ className = 'ds-input', ...props }) {
  const [show, setShow] = useState(false);
  return (
    <div className="pwd-wrap">
      <input {...props} type={show ? 'text' : 'password'} className={className} />
      <button
        type="button"
        className="pwd-toggle"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? 'Ocultar senha' : 'Mostrar senha'}
        title={show ? 'Ocultar senha' : 'Mostrar senha'}
        tabIndex={-1}
      >
        {show ? '🙈' : '👁️'}
      </button>
    </div>
  );
}
