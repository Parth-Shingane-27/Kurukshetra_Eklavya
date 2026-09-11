export function TextField({ label, name, type = "text", value, onChange, error, hint, required, ...rest }) {
  return (
    <div className={`field${error ? " invalid" : ""}`}>
      <label htmlFor={name}>
        {label}
        {required ? " *" : ""}
      </label>
      <input id={name} name={name} type={type} value={value} onChange={onChange} {...rest} />
      {hint && !error && <span className="hint">{hint}</span>}
      {error && (
        <span className="field-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

export function SelectField({ label, name, value, onChange, options, error, hint }) {
  return (
    <div className={`field${error ? " invalid" : ""}`}>
      <label htmlFor={name}>{label}</label>
      <select id={name} name={name} value={value} onChange={onChange}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {hint && !error && <span className="hint">{hint}</span>}
      {error && (
        <span className="field-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
