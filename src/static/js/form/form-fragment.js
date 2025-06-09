function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;

}

$(document).ready(function () {
    $('[id$="-accounts-list"]').click(function () {
        let csrfToken = getCSRFToken(); // Get CSRF token
		$.ajax({
			url: "{% url 'get_accounts_list' %}",
			type: "GET",
			// headers: { "X-CSRFToken": csrfToken , // Send CSRF token in headers#}
			data: {csrfmiddlewaretoken: csrfToken },
			success: function (response) {
                const $newForm = $(response.form_html);
                $('.modal-body').html($newForm);

			}
		});
    });

$('#select-account-{{ uniqueid }}').click(function () {
    console.log('aa')
        const $context = $(this).closest('.modal');
        // 2. حسابِ انتخاب‑شده در همان درخت
        const $checked = $context.find('input[name="names"]:checked');

        if ($checked.length === 0) {
            alert('لطفاً یک حساب را از درخت انتخاب کنید.');
            return;
        }

        const accId   = $checked.val();
        const accName = $.trim($checked[0].nextSibling.nodeValue);

        const $select = $("select[id$='{{ uniqueid }}-balance-account']");
        console.log($select)

        // اگر گزینه هنوز وجود ندارد، بساز
        if (!$select.find(`option[value="${accId}"]`).length) {
            $select.append(`<option value="${accId}">${accName}</option>`);
        }

        // 4. انتخاب و اعلام تغییر
        $select.val(accId).trigger('change');
    });
});
