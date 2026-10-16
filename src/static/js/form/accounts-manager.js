(function ($) {
    'use strict';

    const $config = $('#accounts-manager-config');
    if (!$config.length) return;

    const urls = {
        list: $config.data('list-url'),
        create: $config.data('create-url'),
        edit: $config.data('edit-url-template'),
        delete: $config.data('delete-url-template'),
        move: $config.data('move-url-template')
    };
    const treeId = 'default';
    const treeSelector = `#${treeId}-accounts_tree`;
    const supportsDesktopDrag = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    let movePending = false;
    let mobileMove = {sourceId: null, targetId: null};

    function csrfToken() {
        return $config.find('[name=csrfmiddlewaretoken]').val();
    }

    function urlFor(template, id) {
        return template.replace(/\/0\/$/, `/${id}/`);
    }

    function escapeHtml(value) {
        return $('<div>').text(value == null ? '' : String(value)).html();
    }

    function normalizeText(value) {
        return String(value || '')
            .replace(/ي/g, 'ی')
            .replace(/ك/g, 'ک')
            .replace(/\u200c/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
            .toLocaleLowerCase('fa');
    }

    function treeInstance() {
        return $(treeSelector).jstree(true);
    }

    function nodePath(tree, nodeOrId) {
        const node = tree.get_node(nodeOrId);
        if (!node || node.id === '#') return 'سطح اصلی';
        if (node.data && node.data.path) return node.data.path;

        const names = node.parents
            .filter(id => id !== '#')
            .reverse()
            .map(id => tree.get_text(id));
        names.push(tree.get_text(node));
        return names.join(' > ');
    }

    function parentPath(tree, node) {
        return node.parent === '#' ? 'سطح اصلی' : nodePath(tree, node.parent);
    }

    function addControlsToNodes() {
        const tree = treeInstance();
        if (!tree) return;

        tree.get_json('#', {flat: true}).forEach(node => {
            const $anchor = tree.get_node(node.id, true).children('.jstree-anchor');
            if (!$anchor.length || $anchor.find('.account-node-actions').length) return;

            const controls = `
                <span class="account-node-actions">
                    <button type="button" class="btn btn-sm account-node-action btn-edit"
                            data-id="${node.id}" title="ویرایش حساب" aria-label="ویرایش حساب">📝</button>
                    <button type="button" class="btn btn-sm account-node-action btn-delete"
                            data-id="${node.id}" title="حذف حساب" aria-label="حذف حساب">🗑</button>
                    <button type="button" class="btn btn-sm account-node-action btn-add-child"
                            data-id="${node.id}" title="افزودن زیرحساب" aria-label="افزودن زیرحساب">➕</button>
                    <button type="button" class="btn btn-sm btn-outline-primary account-node-action btn-move-account"
                            data-id="${node.id}" title="جابجایی حساب" aria-label="جابجایی حساب">↔</button>
                </span>`;
            $anchor.append(controls);
        });
    }

    function createTree(data) {
        const $tree = $(treeSelector);
        if (!$tree.length) return;

        $tree.jstree('destroy');
        const plugins = ['wholerow', 'search'];
        if (supportsDesktopDrag) plugins.push('dnd');

        $tree.jstree({
            core: {
                data,
                check_callback(operation, node, parent) {
                    if (operation !== 'move_node') return true;
                    if (movePending || !supportsDesktopDrag) return false;
                    if (!node || !parent || parent.id === node.id) return false;
                    return !(parent.parents || []).includes(node.id);
                },
                themes: {stripes: true, responsive: true}
            },
            dnd: {
                touch: false,
                drag_selection: false,
                always_copy: false,
                large_drop_target: true
            },
            search: {show_only_matches: false},
            plugins
        })
            .on('ready.jstree refresh.jstree open_node.jstree', addControlsToNodes)
            .on('move_node.jstree', function (_event, moveData) {
                if (supportsDesktopDrag) confirmDesktopMove(moveData);
            });
    }

    function loadTree(selectedId) {
        const tree = treeInstance();
        const opened = tree
            ? tree.get_json('#', {flat: true}).filter(node => node.state.opened).map(node => node.id)
            : [];

        return $.getJSON(urls.list).then(response => {
            if (!tree) {
                $('#accounts-report').html(response.form_html);
                createTree(response.data);
                bindTreeSearch();
                return;
            }

            tree.settings.core.data = response.data;
            $(treeSelector).one('refresh.jstree.accountsManagerRestore', function () {
                opened.forEach(id => tree.open_node(id));
                if (selectedId && tree.get_node(String(selectedId))) {
                    tree.deselect_all();
                    tree.select_node(String(selectedId));
                    tree.open_node(tree.get_node(String(selectedId)).parent);
                }
            });
            tree.refresh(true, true);
        });
    }

    function bindTreeSearch() {
        let timer = null;
        $('#default-jstree-search').off('.accountsManager').on('input.accountsManager', function () {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => {
                const tree = treeInstance();
                if (tree) tree.search($(this).val());
            }, 200);
        });
    }

    async function requestMove(sourceId, parentId, position) {
        const response = await fetch(urlFor(urls.move, sourceId), {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken()
            },
            body: JSON.stringify({parent_id: parentId, position})
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.success) {
            throw new Error(payload.error || 'جابجایی حساب انجام نشد.');
        }
        return payload;
    }

    async function confirmDesktopMove(moveData) {
        if (movePending) return;
        movePending = true;

        const tree = treeInstance();
        const sourcePath = moveData.node.data?.path || moveData.node.text;
        const parentLabel = moveData.parent === '#' ? 'سطح اصلی' : nodePath(tree, moveData.parent);
        const positionLabel = Number(moveData.position) + 1;
        const result = await Swal.fire({
            title: 'تأیید جابجایی حساب',
            html: `<div class="text-end"><div><strong>حساب:</strong> ${escapeHtml(sourcePath)}</div>` +
                `<div class="mt-2"><strong>مقصد:</strong> ${escapeHtml(parentLabel)}</div>` +
                `<div class="mt-1"><strong>جایگاه:</strong> ${positionLabel}</div></div>`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'تأیید جابجایی',
            cancelButtonText: 'انصراف',
            reverseButtons: true
        });

        if (!result.isConfirmed) {
            await loadTree(moveData.node.id);
            movePending = false;
            return;
        }

        try {
            await requestMove(
                Number(moveData.node.id),
                moveData.parent === '#' ? null : Number(moveData.parent),
                Number(moveData.position)
            );
            await loadTree(moveData.node.id);
            await Swal.fire({icon: 'success', title: 'حساب جابجا شد', timer: 1200, showConfirmButton: false});
        } catch (error) {
            await loadTree(moveData.node.id);
            await Swal.fire('خطا', error.message, 'error');
        } finally {
            movePending = false;
        }
    }

    function openMoveDialog(sourceId) {
        const tree = treeInstance();
        const node = tree && tree.get_node(String(sourceId));
        if (!node || movePending) return;

        mobileMove = {sourceId: String(sourceId), targetId: null};
        tree.deselect_all();
        tree.select_node(node);
        tree.get_node(node, true).children('.jstree-anchor').addClass('account-move-source');

        $('#account-move-source-label').text(`حساب مبدأ: ${nodePath(tree, node)}`);
        $('#account-move-search').val('');
        $('#account-move-positions').prop('hidden', true);
        $('#account-move-dialog').prop('hidden', false).attr('aria-hidden', 'false');
        $('body').css('overflow', 'hidden');
        renderMoveResults('');
        window.setTimeout(() => $('#account-move-search').trigger('focus'), 0);
    }

    function closeMoveDialog() {
        const tree = treeInstance();
        if (tree && mobileMove.sourceId) {
            tree.get_node(mobileMove.sourceId, true).children('.jstree-anchor').removeClass('account-move-source');
        }
        mobileMove = {sourceId: null, targetId: null};
        $('#account-move-dialog').prop('hidden', true).attr('aria-hidden', 'true');
        $('body').css('overflow', '');
    }

    function validMoveTargets(tree) {
        return tree.get_json('#', {flat: true}).filter(node => {
            if (node.id === mobileMove.sourceId) return false;
            const liveNode = tree.get_node(node.id);
            return !(liveNode.parents || []).includes(mobileMove.sourceId);
        });
    }

    function renderMoveResults(rawQuery) {
        const tree = treeInstance();
        if (!tree || !mobileMove.sourceId) return;

        mobileMove.targetId = null;
        $('#account-move-positions').prop('hidden', true);
        const query = normalizeText(rawQuery);
        const targets = validMoveTargets(tree).filter(node => {
            const liveNode = tree.get_node(node.id);
            return !query || normalizeText(`${nodePath(tree, liveNode)} ${liveNode.text}`).includes(query);
        }).slice(0, 50);

        const rootMatches = !query || normalizeText('سطح اصلی ریشه').includes(query);
        let html = rootMatches ? `
            <button type="button" class="account-move-result" data-target-id="#">
                <strong>سطح اصلی</strong>
                <span class="account-move-result-path">قرار دادن حساب در انتهای حساب‌های ریشه</span>
            </button>` : '';

        html += targets.map(node => {
            const liveNode = tree.get_node(node.id);
            return `
                <button type="button" class="account-move-result" data-target-id="${node.id}">
                    <strong>${escapeHtml(liveNode.text)}</strong>
                    <span class="account-move-result-path">والد: ${escapeHtml(parentPath(tree, liveNode))}</span>
                </button>`;
        }).join('');

        if (!html) {
            html = '<div class="alert alert-light border mb-0">حسابی با این عبارت پیدا نشد.</div>';
        }
        $('#account-move-results').html(html);
    }

    function selectMoveTarget(targetId, $button) {
        const tree = treeInstance();
        mobileMove.targetId = String(targetId);
        $('.account-move-result').removeClass('is-selected');
        $button.addClass('is-selected');

        const isRoot = mobileMove.targetId === '#';
        const label = isRoot ? 'مقصد: سطح اصلی' : `مقصد: ${nodePath(tree, mobileMove.targetId)}`;
        $('#account-move-target-label').text(label);
        $('.account-move-position[data-relation="inside"], .account-move-position[data-relation="before"], .account-move-position[data-relation="after"]')
            .prop('hidden', isRoot);
        $('.account-move-root-position').prop('hidden', !isRoot);
        $('#account-move-positions').prop('hidden', false);
    }

    function movePayloadForRelation(relation) {
        const tree = treeInstance();
        const sourceId = mobileMove.sourceId;
        const targetId = mobileMove.targetId;

        if (relation === 'root') {
            const roots = tree.get_node('#').children.filter(id => id !== sourceId);
            return {parentId: null, position: roots.length, description: 'انتهای سطح اصلی'};
        }

        const target = tree.get_node(targetId);
        if (!target || target.id === '#') return null;

        if (relation === 'inside') {
            const children = target.children.filter(id => id !== sourceId);
            return {
                parentId: Number(target.id),
                position: children.length,
                description: `زیرمجموعه «${nodePath(tree, target)}»`
            };
        }

        const parent = tree.get_node(target.parent);
        const siblings = parent.children.filter(id => id !== sourceId);
        const targetIndex = siblings.indexOf(target.id);
        if (targetIndex < 0) return null;
        const isAfter = relation === 'after';
        return {
            parentId: target.parent === '#' ? null : Number(target.parent),
            position: targetIndex + (isAfter ? 1 : 0),
            description: `${isAfter ? 'بعد' : 'قبل'} از «${nodePath(tree, target)}»`
        };
    }

    async function confirmMobileMove(relation) {
        if (movePending || !mobileMove.sourceId || !mobileMove.targetId) return;
        const tree = treeInstance();
        const payload = movePayloadForRelation(relation);
        if (!payload) return;

        const sourceId = mobileMove.sourceId;
        const sourcePath = nodePath(tree, sourceId);
        const result = await Swal.fire({
            title: 'تأیید جابجایی حساب',
            html: `<div class="text-end"><div><strong>حساب:</strong> ${escapeHtml(sourcePath)}</div>` +
                `<div class="mt-2"><strong>جایگاه جدید:</strong> ${escapeHtml(payload.description)}</div></div>`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'تأیید جابجایی',
            cancelButtonText: 'انصراف',
            reverseButtons: true
        });
        if (!result.isConfirmed) return;

        movePending = true;
        try {
            await requestMove(Number(sourceId), payload.parentId, payload.position);
            closeMoveDialog();
            await loadTree(sourceId);
            await Swal.fire({icon: 'success', title: 'حساب جابجا شد', timer: 1200, showConfirmButton: false});
        } catch (error) {
            await Swal.fire('خطا', error.message, 'error');
        } finally {
            movePending = false;
        }
    }

    function appendNodeForm(nodeId, isEdit) {
        const tree = treeInstance();
        const $node = tree.get_node(String(nodeId), true);
        if (!$node.length || $node.find('> .node-form-container').length) return;

        const currentText = isEdit ? tree.get_text(String(nodeId)) : '';
        const $input = $('<input>', {
            type: 'text',
            class: 'form-control form-control-sm me-2 d-inline-block',
            value: currentText,
            css: {width: '60%', maxWidth: '250px'}
        });
        const $save = $('<button type="button" class="btn btn-sm btn-success me-1">💾</button>');
        const $cancel = $('<button type="button" class="btn btn-sm btn-outline-secondary">❌</button>');
        const $form = $('<div class="node-form-container mt-1 d-flex align-items-center"></div>')
            .append($input, $save, $cancel);
        $node.append($form);
        $input.trigger('focus');

        $cancel.on('click', () => $form.remove());
        $save.on('click', function () {
            const name = $input.val().trim();
            if (!name) {
                Swal.fire('خطا', 'نام حساب نباید خالی باشد.', 'error');
                return;
            }

            const request = isEdit
                ? $.post(urlFor(urls.edit, nodeId), {name, csrfmiddlewaretoken: csrfToken()})
                : $.post(urls.create, {name, parent: nodeId, csrfmiddlewaretoken: csrfToken()});
            request.done(response => {
                if (response.success) loadTree(isEdit ? nodeId : response.id);
                else Swal.fire('خطا', response.error || 'ذخیره حساب انجام نشد.', 'error');
            }).fail(() => Swal.fire('خطا', 'ارتباط با سرور برقرار نشد.', 'error'));
        });
    }

    $(document)
        .on('mousedown.accountsManager touchstart.accountsManager click.accountsManager', '.account-node-action', function (event) {
            event.stopPropagation();
        })
        .on('click.accountsManager', '.btn-edit', function () {
            appendNodeForm($(this).data('id'), true);
        })
        .on('click.accountsManager', '.btn-add-child', function () {
            appendNodeForm($(this).data('id'), false);
        })
        .on('click.accountsManager', '.btn-delete', function () {
            const nodeId = $(this).data('id');
            Swal.fire({
                title: 'حذف حساب؟',
                text: 'آیا مطمئن هستید؟ این عملیات قابل بازگشت نیست!',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'بله، حذف کن',
                cancelButtonText: 'انصراف'
            }).then(result => {
                if (!result.isConfirmed) return;
                $.post(urlFor(urls.delete, nodeId), {csrfmiddlewaretoken: csrfToken()})
                    .done(response => {
                        if (response.success) {
                            loadTree();
                            Swal.fire('حذف شد', 'حساب با موفقیت حذف شد.', 'success');
                        } else {
                            Swal.fire('خطا', response.error || 'حذف حساب انجام نشد.', 'error');
                        }
                    })
                    .fail(() => Swal.fire('خطا', 'ارتباط با سرور برقرار نشد.', 'error'));
            });
        })
        .on('click.accountsManager', '.btn-move-account', function () {
            openMoveDialog($(this).data('id'));
        })
        .on('click.accountsManager', '.add-root-btn', function () {
            if ($('#default-new_root_input_row').length) return;
            const $input = $('<input type="text" class="form-control form-control-sm me-2" placeholder="نام حساب ریشه‌ای">');
            const $save = $('<button type="button" class="btn btn-sm btn-success me-1">💾</button>');
            const $cancel = $('<button type="button" class="btn btn-sm btn-outline-secondary">❌</button>');
            const $row = $('<div id="default-new_root_input_row" class="mb-2 d-flex align-items-center"></div>')
                .append($input, $save, $cancel);
            $(this).after($row);
            $input.trigger('focus');
            $cancel.on('click', () => $row.remove());
            $save.on('click', function () {
                const name = $input.val().trim();
                if (!name) return;
                $.post(urls.create, {name, csrfmiddlewaretoken: csrfToken()}).done(response => {
                    if (response.success) loadTree(response.id);
                    else Swal.fire('خطا', 'افزودن حساب انجام نشد.', 'error');
                });
            });
        });

    $('#account-move-search').on('input', function () {
        renderMoveResults($(this).val());
    });
    $('#account-move-results').on('click', '.account-move-result', function () {
        selectMoveTarget($(this).data('target-id'), $(this));
    });
    $('.account-move-position').on('click', function () {
        confirmMobileMove($(this).data('relation'));
    });
    $('.account-move-close').on('click', closeMoveDialog);
    $('#account-move-dialog').on('click', function (event) {
        if (event.target === this && !movePending) closeMoveDialog();
    });
    $(document).on('keydown.accountsManager', function (event) {
        if (event.key === 'Escape' && !$('#account-move-dialog').prop('hidden') && !movePending) {
            closeMoveDialog();
        }
    });

    $.getJSON(urls.list)
        .done(response => {
            $('#accounts-report').html(response.form_html);
            createTree(response.data);
            bindTreeSearch();
        })
        .fail(() => Swal.fire('خطا', 'دریافت فهرست حساب‌ها انجام نشد.', 'error'));
})(jQuery);
