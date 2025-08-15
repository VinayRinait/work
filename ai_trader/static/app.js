document.addEventListener('DOMContentLoaded',()=>{
	const chips=document.querySelectorAll('.chip');
	const rows=[...document.querySelectorAll('#signals-table tbody tr')];
	chips.forEach(ch=>{
		ch.addEventListener('click',()=>{
			const f=ch.getAttribute('data-filter');
			chips.forEach(c=>c.classList.remove('active'));
			ch.classList.add('active');
			rows.forEach(r=>{
				if(f==='all') { r.style.display=''; return; }
				r.style.display = (r.getAttribute('data-action')===f) ? '' : 'none';
			});
		});
	});
});