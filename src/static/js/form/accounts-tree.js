function getCSRFToken() {
return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

document.querySelectorAll('.toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        const parent = btn.closest('li');
        const children = parent.querySelector('.children');
        if (children) {
            children.style.display = children.style.display === 'block' ? 'none' : 'block';
        }
    });
});

$(document).ready(function () {
    let csrfToken = getCSRFToken(); // Get CSRF token

    $('.create-account-form').on('submit', function (e) {
        e.preventDefault();
        const $form = $(this);

        $.ajax({
            url: "{% url 'create_accounts' %}",
            method: "POST",
            data: $(this).serialize(),
            headers: { "X-CSRFToken": csrfToken },
            success: function (data) {
                if (data.success) {
                    addAccountToTree(data.id, data.name, data.parent_id, $form);
                    $form.closest('.modal').modal('hide');

                    const $wrapper   = $form.closest('.form-wrapper');
                    const $select = $wrapper.find('[id$="-balance-account"]').first();
                    if ($select.length) {
                        // اگه گزینه قبلاً نبود، اضافه کن
                        if (!$select.find(`option[value="${data.id}"]`).length) {
                            $select.append(`<option value="${data.id}" selected>${data.name}</option>`);
                        }}

                } else {
                    alert("خطا: " + JSON.stringify(data.errors));
                }
            }
        });
    });

function addAccountToTree(id, name, parentId, $formContext) {
    const $newLi = $(`
        <li>
            <span class="toggle">▶</span>
            <input class="form-check-input" type="radio" name="names" value="${id}" checked>
            ${name}
            <ul class="children" style="display: none;"></ul>
        </li>
    `);

    // اضافه کردن قابلیت باز/بستن درخت به toggle
    $newLi.find('.toggle').on('click', function () {
        const $children = $(this).siblings('.children');
        $children.slideToggle();
    });

    // اگر parentId وجود داشته باشه (نود فرزند باشه)
    if (parentId) {
        const $parentRadio = $(`input[name="names"][value="${parentId}"]`);
        const $parentLi = $parentRadio.closest('li');

        // بررسی وجود children
        let $childrenContainer = $parentLi.children('ul.children');
        if ($childrenContainer.length === 0) {
            $childrenContainer = $('<ul class="children" style="display: none;"></ul>');
            $parentLi.append($childrenContainer);
        }

        // اضافه کردن toggle اگر وجود نداشته باشه
        if ($parentLi.find('> .toggle').length === 0) {
            const $toggle = $('<span class="toggle">▶</span>');
            $parentLi.prepend($toggle);
            $toggle.on('click', function () {
                $parentLi.children('ul.children').slideToggle();
            });
        }

        $childrenContainer.append($newLi).slideDown();
    }

    // اگر parentId نداشته باشه (یعنی نود ریشه باشه)
    else {
        const $treeContainer = $formContext.closest('.modal, .collapse, .address-check-block')
                                           .find('ul').first();

        // بررسی کن که اگر toggle برای نود ریشه نیاز نیست، حذفش کن (چون فرزند نداره)
        $newLi.find('.children').remove(); // حذف ul خالی
        $newLi.find('.toggle').remove(); // حذف دکمه باز/بسته

        $treeContainer.append($newLi);
    }

    // انتخاب خودکار نود جدید
    $newLi.find('input[type=radio]').prop('checked', true);
}

});