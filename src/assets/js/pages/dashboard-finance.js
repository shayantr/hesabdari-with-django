'use strict';
document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
        floatchart()
    }, 100);
});

function floatchart() {
  (function () {
    var total_line_1_chart_options = {
        chart: {
          type: 'line',
          height: 60,
          sparkline: {
            enabled: true
          }
        },
        dataLabels: {
          enabled: false
        },
        colors: ['#1de9b6'],
        stroke: {
          curve: 'straight',
          lineCap: 'round',
          width: 3
        },
        series: [
          {
            name: 'سری 1',
            data: [20, 10, 18, 12, 25, 10, 20]
          }
        ],
        yaxis: {
          min: 0,
          max: 30
        },
        tooltip: {
          theme: 'dark',
          fixed: {
            enabled: false
          },
          x: {
            show: false
          },
          y: {
            title: {
              formatter: function (seriesName) {
                return '';
              }
            }
          },
          marker: {
            show: false
          }
        }
    }
    var chart = new ApexCharts(document.querySelector("#total-line-1-chart"), total_line_1_chart_options);
    chart.render();

    var total_line_2_chart_options = {
        chart: {
            type: 'line',
            height: 60,
            sparkline: {
              enabled: true
            }
          },
          dataLabels: {
            enabled: false
          },
          colors: ['#1de9b6'],
          stroke: {
            curve: 'straight',
            lineCap: 'round',
            width: 3
          },
          series: [
            {
              name: 'سری 1',
              data: [20, 10, 18, 12, 25, 10, 20]
            }
          ],
          yaxis: {
            min: 0,
            max: 30
          },
          tooltip: {
            theme: 'dark',
            fixed: {
              enabled: false
            },
            x: {
              show: false
            },
            y: {
              title: {
                formatter: function (seriesName) {
                  return '';
                }
              }
            },
            marker: {
              show: false
            }
          }
    }
    var chart = new ApexCharts(document.querySelector("#total-line-2-chart"), total_line_2_chart_options);
    chart.render();

    var total_line_3_chart_options = {
        chart: {
            type: 'line',
            height: 60,
            sparkline: {
              enabled: true
            }
          },
          dataLabels: {
            enabled: false
          },
          colors: ['#f44236'],
          stroke: {
            curve: 'straight',
            lineCap: 'round',
            width: 3
          },
          series: [
            {
              name: 'سری1 ',
              data: [20, 10, 18, 12, 25, 10, 20]
            }
          ],
          yaxis: {
            min: 0,
            max: 30
          },
          tooltip: {
            theme: 'dark',
            fixed: {
              enabled: false
            },
            x: {
              show: false
            },
            y: {
              title: {
                formatter: function (seriesName) {
                  return '';
                }
              }
            },
            marker: {
              show: false
            }
          }
    }
    var chart = new ApexCharts(document.querySelector("#total-line-3-chart"), total_line_3_chart_options);
    chart.render();
    
    var cashflow_bar_chart_options = {
        chart: {
          type: 'bar',
          height: 210,
          toolbar: {
            show: false
          }
        },
        plotOptions: {
          bar: {
            columnWidth: '70%',
            borderRadius: 2
          }
        },
        fill:{
            opacity:[1,0.4],
        },
        stroke: {
          show: true,
          width: 3,
          colors: ['transparent']
        },
        dataLabels: {
          enabled: false
        },
        legend: {
          position: 'top',
          horizontalAlign: 'right',
          show: true,
          fontFamily: `'Vazirmatn', sans-serif`,
          offsetX: 10,
          offsetY: 10,
          labels: {
            useSeriesColors: false
          },
          markers: {
            width: 10,
            height: 10,
            radius: '50%',
            offsexX: 2,
            offsexY: 2
          },
          itemMargin: {
            horizontal: 15,
            vertical: 5
          }
        },
        colors: ['#04a9f5', '#04a9f5'],
        series: [{
          name: 'ورودی',
          data: [180, 90, 135, 114, 120, 145, 180, 90, 135, 114, 120, 145]
        }, {
          name: 'خروجی',
          data: [120, 45, 78, 150, 168, 99, 120, 45, 78, 150, 168, 99]
        }],
        grid:{
          borderColor: '#00000010',
        },
        yaxis: {
          show:false
        }
    }
    var chart = new ApexCharts(document.querySelector("#cashflow-bar-chart"), cashflow_bar_chart_options);
    chart.render();

    var options = {
      chart: {
        height: 300,
        type: 'donut',
      },
      dataLabels: {
        enabled: false
      },
      legend:{
        show:true,
        position: 'bottom',
        fontFamily: `'Vazirmatn', sans-serif`,
      },
      plotOptions: {
        pie: {
          donut: {
            size: '65%'
          }
        }
      },
      labels: ['ذخیره', 'واگذاری', 'ورودی'],
      series: [25, 50, 25],
      colors: ['#212529', '#04a9f5', '#caedfd']
    }
    var chart = new ApexCharts(document.querySelector("#category-donut-chart"), options);
    chart.render();
  })();
}