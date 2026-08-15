document.addEventListener('click', e => {
  const sb = document.getElementById('sidebar');
  if (sb?.classList.contains('open') && !sb.contains(e.target) && !document.querySelector('.menu-btn')?.contains(e.target))
    sb.classList.remove('open');
});
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sfill').forEach(el => {
    const w = el.style.width; el.style.width = '0';
    setTimeout(() => el.style.width = w, 120);
  });
});
