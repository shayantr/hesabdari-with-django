'use strict';
(function () {
// [ html-demo ]
const main = document.querySelector('#tree-demo');
const info = document.querySelector('#tree-msg');

const tree = new VanillaTree(main, {
  contextmenu: [
    {
      label: 'سلام',
      action: function (id) {
        alert('Hey ' + id);
      }
    },
    {
      label: 'ایول',
      action: function (id) {
        alert('بله ' + id);
      }
    }
  ]
});

tree.add({
  label: 'لیبل A',
  id: 'a',
  opened: true
});

tree.add({
  label: 'لیبل B',
  id: 'b'
});

tree.add({
  label: 'لیبل A.A',
  parent: 'a',
  id: 'a.a',
  opened: true,
  selected: true
});

tree.add({
  label: 'لیبل A.A.A',
  parent: 'a.a'
});

tree.add({
  label: 'لیبل A.A.B',
  parent: 'a.a'
});

tree.add({
  label: 'لیبل B.A',
  parent: 'b'
});

main.addEventListener('vtree-open', function (evt) {
  info.innerHTML = evt.detail.id + ' باز می شود';
});

main.addEventListener('vtree-close', function (evt) {
  info.innerHTML = evt.detail.id + ' بسته است';
});

main.addEventListener('vtree-select', function (evt) {
  info.innerHTML = evt.detail.id + ' انتخاب شده';
});
})();