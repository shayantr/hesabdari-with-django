'use strict';
(function () {
document.addEventListener('DOMContentLoaded', function () {
  introJs()
    .setOptions({
      steps: [
        {
          intro: 'سلام دنیا!'
        },
        {
          element: document.querySelector('.step1'),
          intro: 'این کارت است'
        },
        {
          element: document.querySelector('.step2'),
          intro: 'این هدر کارت است'
        },
        {
          element: document.querySelector('.step3'),
          intro: 'این عنوان کارت است'
        },
        {
          element: document.querySelector('.step4'),
          intro: 'این بدنه کارت است'
        }
      ]
    })
    .start();
});
})();
