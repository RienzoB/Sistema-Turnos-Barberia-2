// Validación rápida en el formulario de agendar turno
document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', (e) => {
            const nombre = form.nombre.value.trim();
            const email = form.email.value.trim();
            const fechaHora = form.fecha_hora.value;

            if (!nombre || !email || !fechaHora) {
                alert('Todos los campos son obligatorios.');
                e.preventDefault();
            }
        });
    }
});