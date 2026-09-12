export function TextField({ label, name, type = "text", value, onChange, error, hint, required, help, ...rest }) {
  return (
    <div className={`field${error ? " invalid" : ""}`}>
      <label htmlFor={name}>
        {label}
        {required ? " *" : ""}
        {help}
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

export function SelectField({ label, name, value, onChange, options, error, hint, help }) {
  return (
    <div className={`field${error ? " invalid" : ""}`}>
      <label htmlFor={name}>
        {label}
        {help}
      </label>
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
