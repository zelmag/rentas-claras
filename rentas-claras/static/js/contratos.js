        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2000);
        }
        
        function updateCounts() {
            let renewing = 0;
            let notRenewing = 0;
            let pending = 0;
            
            document.querySelectorAll('.contract-card').forEach(card => {
                if (card.classList.contains('renewing')) renewing++;
                else if (card.classList.contains('not-renewing')) notRenewing++;
                else pending++;
            });
            
            document.getElementById('renewingCount').textContent = renewing;
            document.getElementById('notRenewingCount').textContent = notRenewing;
            document.getElementById('pendingCount').textContent = pending;
        }
        
        function setRenewalStatus(btn, tenantId, status) {
            const card = btn.closest('.contract-card');
            const container = btn.closest('.renewal-buttons');
            
            // Update button states
            container.querySelectorAll('.renewal-btn').forEach(b => {
                b.classList.remove('active-green', 'active-red', 'active-yellow');
            });
            
            // Set active state and card style
            card.classList.remove('renewing', 'not-renewing', 'pending');
            
            if (status === 'renovará') {
                btn.classList.add('active-green');
                card.classList.add('renewing');
            } else if (status === 'no_renovará') {
                btn.classList.add('active-red');
                card.classList.add('not-renewing');
            } else {
                btn.classList.add('active-yellow');
                card.classList.add('pending');
            }
            
            // Show/hide replacement section
            const replacementSection = document.getElementById(`replacement-${tenantId}`);
            if (replacementSection) {
                replacementSection.style.display = status === 'no_renovará' ? 'block' : 'none';
            }
            
            // Save to database
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    renewal_status: status
                })
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                    updateCounts();
                }
            });
        }
        
        function updateContractDelivery(checkbox, tenantId, type) {
            const isChecked = checkbox.checked;
            const data = { tenant_id: tenantId };
            
            if (type === 'delivered') {
                data.contract_delivered = isChecked;
            } else if (type === 'picked_up') {
                data.contract_picked_up = isChecked;
            }
            
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    showToast(isChecked ? 'Marcado' : 'Desmarcado');
                }
            });
        }
        
        function updateReplacement(input, tenantId, field) {
            const value = input.value;
            const data = { tenant_id: tenantId };
            
            if (field === 'name') {
                data.replacement_name = value;
            } else if (field === 'phone') {
                data.replacement_phone = value;
            }
            
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                }
            });
        }
        
        // Generic field update function for replacement fields
        function updateReplacementField(input, tenantId, field) {
            const value = input.value;
            const data = { tenant_id: tenantId };
            data[field] = value;
            
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                }
            });
        }
        
        // =============================================
        // INLINE EDITING from Bird's Eye View
        // =============================================
        
        function toggleUpcomingExpand(item, event) {
            // Don't toggle if clicking on form elements inside
            if (event.target.closest('.upcoming-expand-form')) {
                return;
            }
            
            // Close other expanded items
            document.querySelectorAll('.upcoming-item.expanded').forEach(other => {
                if (other !== item) {
                    other.classList.remove('expanded');
                }
            });
            
            // Toggle this item
            item.classList.toggle('expanded');
        }
        
        function setInlineRenewalStatus(tenantId, status, btn) {
            const item = btn.closest('.upcoming-item');
            const container = btn.closest('.inline-renewal-buttons');
            
            // Update button states in the inline form
            container.querySelectorAll('.inline-renewal-btn').forEach(b => {
                b.classList.remove('active-green', 'active-red', 'active-yellow');
            });
            
            // Set active state
            if (status === 'renovará') {
                btn.classList.add('active-green');
            } else if (status === 'no_renovará') {
                btn.classList.add('active-red');
            } else {
                btn.classList.add('active-yellow');
            }
            
            // Update the item's visual state
            item.classList.remove('renewing', 'not-renewing', 'pending');
            if (status === 'renovará') {
                item.classList.add('renewing');
            } else if (status === 'no_renovará') {
                item.classList.add('not-renewing');
            } else {
                item.classList.add('pending');
            }
            
            // Show/hide inline replacement section
            const inlineReplacementSection = document.getElementById(`inline-replacement-${tenantId}`);
            if (inlineReplacementSection) {
                if (status === 'no_renovará') {
                    inlineReplacementSection.classList.remove('hidden');
                } else {
                    inlineReplacementSection.classList.add('hidden');
                }
            }
            
            // Update the status badge in the header
            const statusContainer = item.querySelector('.upcoming-status');
            const statusBadge = statusContainer.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.className = 'status-badge';
                if (status === 'renovará') {
                    statusBadge.classList.add('green');
                    statusBadge.textContent = 'Renovará';
                } else if (status === 'no_renovará') {
                    statusBadge.classList.add('red');
                    statusBadge.textContent = 'No renovará';
                } else {
                    statusBadge.classList.add('yellow');
                    statusBadge.style.background = '#F5F5F5';
                    statusBadge.style.color = '#333333';
                    statusBadge.textContent = 'Pendiente';
                }
            }
            
            // Also update the corresponding contract card below (if visible)
            const contractCard = document.querySelector(`.contract-card[data-tenant-id="${tenantId}"]`);
            if (contractCard) {
                contractCard.classList.remove('renewing', 'not-renewing', 'pending');
                if (status === 'renovará') {
                    contractCard.classList.add('renewing');
                } else if (status === 'no_renovará') {
                    contractCard.classList.add('not-renewing');
                } else {
                    contractCard.classList.add('pending');
                }
                
                // Update buttons in the card
                const cardButtons = contractCard.querySelectorAll('.renewal-btn');
                cardButtons.forEach(b => {
                    b.classList.remove('active-green', 'active-red', 'active-yellow');
                    if (b.textContent.includes('Sí') && status === 'renovará') {
                        b.classList.add('active-green');
                    } else if (b.textContent.includes('No') && status === 'no_renovará') {
                        b.classList.add('active-red');
                    } else if (b.textContent.includes('Pendiente') && status === 'pendiente') {
                        b.classList.add('active-yellow');
                    }
                });
                
                // Show/hide replacement section in card
                const cardReplacementSection = document.getElementById(`replacement-${tenantId}`);
                if (cardReplacementSection) {
                    cardReplacementSection.style.display = status === 'no_renovará' ? 'block' : 'none';
                }
            }
            
            // Save to database
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    renewal_status: status
                })
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                    updateCounts();
                }
            });
        }
        
        function updateInlineReplacement(tenantId, field, value) {
            const data = { tenant_id: tenantId };
            data[field] = value;
            
            // Also update the corresponding input in the contract card below
            const contractCard = document.querySelector(`.contract-card[data-tenant-id="${tenantId}"]`);
            if (contractCard) {
                const correspondingInput = contractCard.querySelector(`input[onchange*="${field}"]`);
                if (correspondingInput) {
                    correspondingInput.value = value;
                }
            }
            
            // Update replacement badge if it's the name field
            if (field === 'replacement_name') {
                const upcomingItem = document.getElementById(`upcoming-${tenantId}`);
                if (upcomingItem) {
                    const replacementBadge = upcomingItem.querySelector('.replacement-badge');
                    if (replacementBadge && value) {
                        replacementBadge.textContent = value;
                        replacementBadge.classList.remove('needs-candidate');
                        replacementBadge.style.background = '#dbeafe';
                        replacementBadge.style.color = '#1d4ed8';
                    } else if (replacementBadge && !value) {
                        replacementBadge.textContent = 'Sin candidato';
                        replacementBadge.classList.add('needs-candidate');
                        replacementBadge.style.background = '#FEE2E2';
                        replacementBadge.style.color = '#CC0000';
                    }
                }
            }
            
            fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(response => {
                if (response.ok) {
                    showToast('Guardado');
                }
            });
        }
        
        // =============================================
        // Search/Filter Contracts
        // =============================================
        
        function filterContracts(searchTerm) {
            const searchInput = document.getElementById('contractSearch');
            const clearBtn = document.getElementById('clearContractSearch');
            const resultsDiv = document.getElementById('contractSearchResults');
            const term = searchTerm.toLowerCase().trim();
            
            // Show/hide clear button using class toggle
            if (term) {
                clearBtn.classList.add('visible');
            } else {
                clearBtn.classList.remove('visible');
            }
            
            // Get all contract cards and property sections
            const allCards = document.querySelectorAll('.contract-card');
            const allPropertySections = document.querySelectorAll('.property-section');
            const allUpcomingItems = document.querySelectorAll('.upcoming-item');
            
            if (!term) {
                // Show all
                allCards.forEach(card => card.style.display = 'block');
                allPropertySections.forEach(section => section.style.display = 'block');
                allUpcomingItems.forEach(item => item.style.display = 'flex');
                resultsDiv.style.display = 'none';
                return;
            }
            
            let matchCount = 0;
            const propertyVisibility = {};
            
            // Filter contract cards
            allCards.forEach(card => {
                const nameEl = card.querySelector('.tenant-name');
                if (!nameEl) return;
                const name = nameEl.textContent.toLowerCase();
                const propertySection = card.closest('.property-section');
                const propertyHeader = propertySection ? propertySection.querySelector('.property-header') : null;
                const propertyName = propertyHeader ? propertyHeader.textContent.trim() : '';
                
                if (name.includes(term)) {
                    card.style.display = 'block';
                    matchCount++;
                    propertyVisibility[propertyName] = true;
                } else {
                    card.style.display = 'none';
                }
            });
            
            // Filter upcoming items
            allUpcomingItems.forEach(item => {
                const nameEl = item.querySelector('.upcoming-name');
                if (!nameEl) return;
                const name = nameEl.textContent.toLowerCase();
                
                if (name.includes(term)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
            
            // Hide property sections with no visible cards
            allPropertySections.forEach(section => {
                const header = section.querySelector('.property-header');
                const propName = header ? header.textContent.trim() : '';
                section.style.display = propertyVisibility[propName] ? 'block' : 'none';
            });
            
            // Show results count
            resultsDiv.style.display = 'block';
            if (matchCount === 0) {
                resultsDiv.innerHTML = `No se encontró "<strong>${searchTerm}</strong>"`;
            } else if (matchCount === 1) {
                resultsDiv.innerHTML = `1 inquilino encontrado`;
            } else {
            resultsDiv.innerHTML = `${matchCount} inquilinos encontrados`;
            }
        }
        
        // =============================================
        // Property Filter Tabs for Contratos
        // =============================================
        
        let activeContractPropertyFilter = 'all';
        
        function filterContractsByProperty(propertyName, btn) {
            activeContractPropertyFilter = propertyName;
            
            // Update tab active states and styles (green active, consistent with Pagos)
            const allTabs = document.querySelectorAll('#propertyFilterTabsContratos .property-filter-tab');
            allTabs.forEach(tab => {
                tab.classList.remove('active');
                tab.style.background = 'transparent';
                tab.style.color = '#333333';
            });
            btn.classList.add('active');
            btn.style.background = '#0A7A0A';
            btn.style.color = 'white';
            
            // Clear any search filter first
            const searchInput = document.getElementById('contractSearch');
            if (searchInput && searchInput.value) {
                searchInput.value = '';
                document.getElementById('clearContractSearch').classList.remove('visible');
                document.getElementById('contractSearchResults').style.display = 'none';
            }
            
            // Filter contract cards
            const allCards = document.querySelectorAll('.contract-card');
            const allPropertySections = document.querySelectorAll('.property-section');
            const allUpcomingItems = document.querySelectorAll('.upcoming-item');
            const availableSection = document.querySelector('.available-section');
            const upcomingSection = document.querySelector('.upcoming-section');
            
            if (propertyName === 'all') {
                // Show all
                allCards.forEach(card => card.style.display = 'block');
                allPropertySections.forEach(section => section.style.display = 'block');
                allUpcomingItems.forEach(item => item.style.display = 'flex');
                if (availableSection) availableSection.style.display = 'block';
                if (upcomingSection) upcomingSection.style.display = 'block';
            } else {
                // Filter by property
                allCards.forEach(card => {
                    const propertySection = card.closest('.property-section');
                    const propertyHeader = propertySection ? propertySection.querySelector('.property-header') : null;
                    const propName = propertyHeader ? propertyHeader.textContent.trim() : '';
                    
                    if (propName.includes(propertyName)) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                });
                
                allPropertySections.forEach(section => {
                    const header = section.querySelector('.property-header');
                    const propName = header ? header.textContent.trim() : '';
                    section.style.display = propName.includes(propertyName) ? 'block' : 'none';
                });
                
                // Filter upcoming items by property name in the text
                allUpcomingItems.forEach(item => {
                    const nameEl = item.querySelector('.upcoming-name');
                    if (!nameEl) return;
                    const name = nameEl.textContent;
                    item.style.display = name.includes(propertyName) ? 'flex' : 'none';
                });
                
                // Hide available apartments section when filtering
                if (availableSection) {
                    const hasMatchingApartments = Array.from(availableSection.querySelectorAll('.available-property')).some(el => 
                        el.textContent.includes(propertyName)
                    );
                    availableSection.style.display = hasMatchingApartments ? 'block' : 'none';
                }
            }
        }
        
        function clearContractSearch() {
            const searchInput = document.getElementById('contractSearch');
            searchInput.value = '';
            filterContracts('');
            searchInput.focus();
        }
