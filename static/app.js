const form = document.querySelector('#form');
if (form) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    for (const key of ['amount (INR)', 'risk_score', 'hour_of_day', 'is_weekend']) {
      data[key] = Number(data[key]);
    }
    const result = document.querySelector('#result');
    const button = form.querySelector('button');
    result.textContent = 'Scoring transaction…';
    button.disabled = true;
    try {
      const response = await fetch('/api/predict', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
      });
      const body = await response.json();
      if (!response.ok) {
        const missing = body.missing_features?.join(', ');
        throw new Error(missing ? `${body.error} ${missing}` : (body.error || 'Request failed.'));
      }
      const percent = (body.fraud_probability * 100).toFixed(1);
      result.textContent = `${body.label} · ${percent}% model score (decision threshold ${body.threshold})`;
      result.style.color = body.prediction ? '#a74d19' : '#165c43';
    } catch (error) {
      result.textContent = `Could not score: ${error.message}`;
      result.style.color = '#a33';
    } finally {
      button.disabled = false;
    }
  });
}
