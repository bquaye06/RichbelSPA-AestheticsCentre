/**
 * Main JavaScript for Rhichbel SPA Frontend
 */

let bookableServicesCache = null;
let bookableServicesPromise = null;

async function fetchBookableServices() {
  if (bookableServicesCache) {
    return bookableServicesCache;
  }

  if (bookableServicesPromise) {
    return bookableServicesPromise;
  }

  bookableServicesPromise = fetch('/api/services?bookable=true')
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      bookableServicesCache = Array.isArray(data) ? data : [];
      return bookableServicesCache;
    })
    .finally(() => {
      bookableServicesPromise = null;
    });

  return bookableServicesPromise;
}

async function loadServices() {
  const serviceList = document.getElementById('service-list');
  const serviceCount = document.getElementById('serviceCount');
  const serviceSearch = document.getElementById('serviceSearch');
  const serviceFilters = document.getElementById('serviceFilters');
  const servicesMeta = document.getElementById('servicesMeta');

  // Services are only rendered on the services page.
  if (!serviceList) {
    return;
  }

  const escapeHtml = (value) => String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const classifyService = (name, variants) => {
    const text = `${name} ${variants.map(v => `${v.variant_name || ''} ${v.notes || ''}`).join(' ')}`.toLowerCase();

    if (/(filler|botox|inject|lip|tox)/.test(text)) return 'Injectables';
    if (/(laser|ipl|light|hair\s*remov)/.test(text)) return 'Laser';
    if (/(facial|cleanse|peel|microderm|hydra|skin)/.test(text)) return 'Facials';
    if (/(body|contour|sculpt|massage|detox|wrap)/.test(text)) return 'Body';
    if (/(brow|lash|thread|wax)/.test(text)) return 'Beauty';

    return 'Specialty';
  };

  const formatServiceCount = (count) => `${count} service${count === 1 ? '' : 's'}`;
  
  try {
    const services = await fetchBookableServices();
    
    if (!services || services.length === 0) {
      serviceList.innerHTML = '<p class="services-empty">No services available at the moment.</p>';
      if (serviceCount) {
        serviceCount.textContent = '0';
      }
      if (servicesMeta) {
        servicesMeta.textContent = 'Showing 0 of 0 services';
      }
      return;
    }
    
    // Group services by service name
    const groupedServices = {};
    services.forEach(service => {
      const name = service.service_name || 'Unknown';
      if (!groupedServices[name]) {
        groupedServices[name] = [];
      }
      groupedServices[name].push(service);
    });
    
    const serviceCards = Object.entries(groupedServices)
      .map(([serviceName, variants]) => ({
        name: serviceName,
        variants,
        category: classifyService(serviceName, variants)
      }))
      .sort((a, b) => a.name.localeCompare(b.name));

    const categories = ['All', ...new Set(serviceCards.map(service => service.category).sort((a, b) => a.localeCompare(b)))];
    let activeCategory = 'All';

    const renderFilters = () => {
      if (!serviceFilters) {
        return;
      }

      serviceFilters.innerHTML = categories.map(category => `
        <button
          type="button"
          class="service-filter-chip${category === activeCategory ? ' is-active' : ''}"
          data-category="${escapeHtml(category)}"
          role="tab"
          aria-selected="${String(category === activeCategory)}"
        >
          ${escapeHtml(category)}
        </button>
      `).join('');

      serviceFilters.querySelectorAll('.service-filter-chip').forEach(button => {
        button.addEventListener('click', () => {
          activeCategory = button.dataset.category || 'All';
          renderFilters();
          renderServices();
        });
      });
    };

    const getFilteredServices = () => {
      const query = (serviceSearch?.value || '').trim().toLowerCase();

      return serviceCards.filter(service => {
        const categoryMatch = activeCategory === 'All' || service.category === activeCategory;
        if (!categoryMatch) {
          return false;
        }

        if (!query) {
          return true;
        }

        const haystack = [
          service.name,
          service.category,
          ...service.variants.map(v => `${v.variant_name || ''} ${v.notes || ''}`)
        ].join(' ').toLowerCase();

        return haystack.includes(query);
      });
    };

    const renderServices = () => {
      const filteredServices = getFilteredServices();

      if (!filteredServices.length) {
        serviceList.innerHTML = '<p class="services-empty">No services match this search yet. Try another keyword or category.</p>';
      } else {
        let html = '';

        filteredServices.forEach(({ name: serviceName, variants }) => {
          html += `
            <div class="service-card">
              <div class="service-card-head">
                <h3>${escapeHtml(serviceName)}</h3>
                <span class="variant-count">${variants.length} option${variants.length > 1 ? 's' : ''}</span>
              </div>
              <div class="variant-list">
          `;

          variants.forEach(v => {
            const amountMin = v.latest_price?.amount_min;
            const amountMax = v.latest_price?.amount_max;
            const currencyCode = v.latest_price?.currency_code || 'GHS';
            const price = v.latest_price
              ? `${currencyCode} ${amountMin}${amountMax && amountMax !== amountMin ? ' - ' + amountMax : ''}`
              : 'Contact for price';

            const metaParts = [];
            if (v.unit_type) {
              metaParts.push(v.unit_type.replace('_', ' '));
            }
            if (v.quantity) {
              metaParts.push(`${v.quantity} unit${v.quantity > 1 ? 's' : ''}`);
            }
            if (v.min_sessions || v.max_sessions) {
              const minSessions = v.min_sessions || v.max_sessions;
              const maxSessions = v.max_sessions || v.min_sessions;
              metaParts.push(`${minSessions}${maxSessions && maxSessions !== minSessions ? '-' + maxSessions : ''} session${(maxSessions || minSessions) > 1 ? 's' : ''}`);
            }

            html += `
              <div class="variant">
                <div class="variant-top">
                  <strong>${escapeHtml(v.variant_name || 'Standard Option')}</strong>
                  <div class="price">${escapeHtml(price)}</div>
                </div>
                ${metaParts.length ? `<div class="variant-meta">${escapeHtml(metaParts.join(' • '))}</div>` : ''}
                ${v.notes ? `<p class="variant-note">${escapeHtml(v.notes)}</p>` : ''}
              </div>
            `;
          });

          html += '</div></div>';
        });

        serviceList.innerHTML = html;
      }

      if (serviceCount) {
        serviceCount.textContent = String(serviceCards.length);
      }
      if (servicesMeta) {
        servicesMeta.textContent = `Showing ${formatServiceCount(filteredServices.length)} of ${formatServiceCount(serviceCards.length)}`;
      }
    };

    renderFilters();
    renderServices();

    if (serviceSearch) {
      serviceSearch.addEventListener('input', renderServices);
    }
  } catch (error) {
    console.error('Error loading services:', error);
    serviceList.innerHTML = '<p class="services-empty">Error loading services. Please try again later.</p>';
    if (servicesMeta) {
      servicesMeta.textContent = 'Showing 0 of 0 services';
    }
  }
}

// Drawer / side-panel controls
function openPanel() {
  const panel = document.getElementById('sidePanel');
  const overlay = document.getElementById('overlay');
  const btn = document.getElementById('menuBtn');
  panel.classList.add('open');
  panel.setAttribute('aria-hidden', 'false');
  overlay.hidden = false;
  btn.setAttribute('aria-expanded', 'true');
}

function closePanel() {
  const panel = document.getElementById('sidePanel');
  const overlay = document.getElementById('overlay');
  const btn = document.getElementById('menuBtn');
  panel.classList.remove('open');
  panel.setAttribute('aria-hidden', 'true');
  overlay.hidden = true;
  btn.setAttribute('aria-expanded', 'false');
}

function setupDrawer() {
  const menuBtn = document.getElementById('menuBtn');
  const closeBtn = document.getElementById('closeBtn');
  const overlay = document.getElementById('overlay');
  const sideLinks = document.querySelectorAll('.side-link');

  if (menuBtn) menuBtn.addEventListener('click', openPanel);
  if (closeBtn) closeBtn.addEventListener('click', closePanel);
  if (overlay) overlay.addEventListener('click', closePanel);
  sideLinks.forEach(l => l.addEventListener('click', closePanel));
}

function setupBookingFlow() {
  const bookingModal = document.getElementById('bookingModal');
  const bookingTriggers = document.querySelectorAll('a[data-book-appointment]');
  const bookingCloseControls = document.querySelectorAll('[data-booking-close]');
  const appointmentForms = document.querySelectorAll('[data-appointment-form]');
  const serviceSelects = document.querySelectorAll('[data-service-select]');
  const dateInputs = document.querySelectorAll('[data-appointment-date]');

  if (!bookingModal && !appointmentForms.length && !serviceSelects.length) {
    return;
  }

  const modalPanel = bookingModal ? bookingModal.querySelector('.booking-modal-panel') : null;

  const openBookingModal = () => {
    if (!bookingModal) {
      return;
    }

    bookingModal.hidden = false;
    document.body.classList.add('modal-open');
    const firstInput = bookingModal.querySelector('input, select, textarea, button');
    if (firstInput) {
      firstInput.focus();
    }
  };

  const closeBookingModal = () => {
    if (!bookingModal) {
      return;
    }

    bookingModal.hidden = true;
    document.body.classList.remove('modal-open');
  };

  bookingTriggers.forEach(trigger => {
    trigger.addEventListener('click', event => {
      if (!bookingModal) {
        return;
      }

      event.preventDefault();
      openBookingModal();
    });
  });

  bookingCloseControls.forEach(control => {
    control.addEventListener('click', closeBookingModal);
  });

  if (bookingModal) {
    bookingModal.addEventListener('click', event => {
      if (event.target === bookingModal || event.target.classList.contains('booking-modal-backdrop')) {
        closeBookingModal();
      }
    });
  }

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && bookingModal && !bookingModal.hidden) {
      closeBookingModal();
    }
  });

  const populateServiceSelects = async () => {
    if (!serviceSelects.length) {
      return;
    }

    try {
      const services = await fetchBookableServices();
      const grouped = {};

      services.forEach(service => {
        const serviceName = service.service_name || 'Unknown';
        if (!grouped[serviceName]) {
          grouped[serviceName] = [];
        }
        grouped[serviceName].push(service);
      });

      const sortedServices = Object.entries(grouped).sort((a, b) => a[0].localeCompare(b[0]));

      serviceSelects.forEach(select => {
        select.innerHTML = '<option value="">Select a service</option>';

        sortedServices.forEach(([serviceName, variants]) => {
          const optgroup = document.createElement('optgroup');
          optgroup.label = serviceName;

          variants.forEach(variant => {
            const amountMin = variant.latest_price?.amount_min;
            const amountMax = variant.latest_price?.amount_max;
            const currencyCode = variant.latest_price?.currency_code || 'GHS';
            const price = variant.latest_price
              ? `${currencyCode} ${amountMin}${amountMax && amountMax !== amountMin ? ' - ' + amountMax : ''}`
              : 'Contact for price';

            const option = document.createElement('option');
            option.value = variant.variant_id;
            option.textContent = `${variant.variant_name || 'Standard Option'} — ${price}`;
            optgroup.appendChild(option);
          });

          select.appendChild(optgroup);
        });
      });
    } catch (error) {
      console.error('Error loading appointment services:', error);
      serviceSelects.forEach(select => {
        select.innerHTML = '<option value="">Unable to load services</option>';
      });
    }
  };

  const initializeDateInputs = () => {
    const today = new Date();
    const isoDate = today.toISOString().split('T')[0];
    dateInputs.forEach(input => {
      input.min = isoDate;
    });
  };

  const setStatusMessage = (form, message, type) => {
    const statusElement = form.querySelector('[data-form-status]');
    if (!statusElement) {
      return;
    }

    statusElement.textContent = message;
    statusElement.dataset.state = type;
  };

  const normalizeAppointmentTime = (value) => {
    const timeMatch = String(value || '').trim().match(/^([0-1]?\d|2[0-3]):([0-5]\d)$/);
    if (!timeMatch) {
      return null;
    }

    return `${String(Number(timeMatch[1])).padStart(2, '0')}:${timeMatch[2]}`;
  };

  appointmentForms.forEach(form => {
    const appointmentTimeInput = form.querySelector('[name="appointment_time"]');

    if (appointmentTimeInput) {
      appointmentTimeInput.addEventListener('blur', () => {
        const normalized = normalizeAppointmentTime(appointmentTimeInput.value);
        if (normalized) {
          appointmentTimeInput.value = normalized;
          appointmentTimeInput.setCustomValidity('');
        } else if (appointmentTimeInput.value.trim()) {
          appointmentTimeInput.setCustomValidity('Enter a valid time like 9:30 or 17:00.');
        } else {
          appointmentTimeInput.setCustomValidity('');
        }
      });

      appointmentTimeInput.addEventListener('input', () => {
        appointmentTimeInput.setCustomValidity('');
      });
    }

    form.addEventListener('submit', async event => {
      event.preventDefault();

      if (appointmentTimeInput) {
        const normalizedTime = normalizeAppointmentTime(appointmentTimeInput.value);
        if (!normalizedTime) {
          appointmentTimeInput.setCustomValidity('Enter a valid time like 9:30 or 17:00.');
          appointmentTimeInput.reportValidity();
          return;
        }

        appointmentTimeInput.value = normalizedTime;
        appointmentTimeInput.setCustomValidity('');
      }

      const submitButton = form.querySelector('button[type="submit"]');
      if (submitButton) {
        submitButton.disabled = true;
      }

      setStatusMessage(form, 'Submitting your appointment request...', 'loading');

      const payload = Object.fromEntries(new FormData(form).entries());

      try {
        const response = await fetch('/api/appointments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok) {
          const errorMessage = result?.error || 'We could not submit your appointment request right now.';
          throw new Error(errorMessage);
        }

        form.reset();
        setStatusMessage(form, 'Your request has been sent. Our team will confirm your appointment shortly.', 'success');

        if (bookingModal && !bookingModal.hidden) {
          window.setTimeout(() => {
            closeBookingModal();
          }, 1200);
        }
      } catch (error) {
        console.error('Error submitting appointment:', error);
        setStatusMessage(form, error.message || 'Something went wrong. Please try again.', 'error');
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  });

  populateServiceSelects();
  initializeDateInputs();
}

// Load services and wire drawer when DOM is ready
document.addEventListener('DOMContentLoaded', () => { loadServices(); setupDrawer(); setupBookingFlow(); });
