document.addEventListener('DOMContentLoaded', () => {
    const servicioEl = document.getElementById('servicio');
    const fechaEl = document.getElementById('fecha');
    const listaEl = document.getElementById('lista-horarios');
    const hiddenEl = document.getElementById('fecha_hora');

    // 1) Inicializar Flatpickr solo para la fecha
    flatpickr(fechaEl, {
        dateFormat: 'Y-m-d',
        minDate: 'today',
        disable: [d => d.getDay() === 0]  // domingos
    });

    // 2) Función para cargar horarios
    async function cargaHorarios() {
        const fecha = fechaEl.value;
        const servicio = servicioEl.value;
        if (!fecha || !servicio) return;
        listaEl.innerHTML = '<div class="spinner-border text-secondary"></div>';
        try {
            const res = await fetch(`/horarios_disponibles?fecha=${fecha}&servicio=${encodeURIComponent(servicio)}`);
            const horas = await res.json();
            if (!horas.length) {
                listaEl.innerHTML = '<span class="text-danger">No hay horarios disponibles</span>';
                return;
            }
            // Renderizar botones
            listaEl.innerHTML = horas.map(h =>
                `<button type="button" class="btn btn-outline-primary hora-btn">${h}</button>`
            ).join('');
            // Añadir listener a cada botón
            document.querySelectorAll('.hora-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    // Marcar selección
                    document.querySelectorAll('.hora-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    hiddenEl.value = `${fecha}T${btn.textContent}`;
                });
            });
        } catch (e) {
            listaEl.innerHTML = '<span class="text-danger">Error al cargar horarios</span>';
            console.error(e);
        }
    }

    // 3) Disparadores: fecha o servicio cambian
    fechaEl.addEventListener('change', cargaHorarios);
    servicioEl.addEventListener('change', cargaHorarios);

    // 4) Prevenir submit sin elegir hora
    document.getElementById('form-agendar').addEventListener('submit', e => {
        if (!hiddenEl.value) {
            e.preventDefault();
            alert('Por favor, seleccioná un horario.');
        }
    });
});
