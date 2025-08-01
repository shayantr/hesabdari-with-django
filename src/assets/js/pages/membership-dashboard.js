'use strict';
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
        floatchart();
    }, 500);
});

function floatchart() {
    (function () {
        var options = {
            chart: {
                type: 'area',
                height: 300,
                toolbar: {
                  show: false
                }
              },
              colors: ['#f4c22b', '#04a9f5'],
              dataLabels: {
                enabled: false
              },
              legend: {
                fontFamily: `'Vazirmatn', sans-serif`,
                show: true,
                position: 'top'
              },
              markers: {
                size: 1,
                colors: ['#fff', '#fff', '#fff'],
                strokeColors: ['#f4c22b', '#04a9f5'],
                strokeWidth: 1,
                shape: 'circle',
                hover: {
                  size: 4
                }
              },
              stroke: {
                width: 1,
                curve: 'smooth'
              },
              fill: {
                type: 'gradient',
                gradient: {
                  shadeIntensity: 1,
                  type: 'vertical',
                  inverseColors: false,
                  opacityFrom: 0.5,
                  opacityTo: 0
                }
              },
              grid: {
                show: false,
              },
              series: [
                {
                  name: 'درآمد',
                  data: [200, 320, 320, 275, 275, 400, 400, 300, 440, 320, 320, 275, 275, 400, 300, 440]
                },
                {
                  name: 'فروش',
                  data: [200, 250, 240, 300, 340, 320, 320, 400, 350, 250, 240, 300, 340, 320, 400, 350]
                }
              ],
              xaxis: {
                labels: {
                  hideOverlappingLabels: true
                },
                axisBorder: {
                  show: false
                },
                axisTicks: {
                  show: false
                }
              }
        };
        var chart = new ApexCharts(document.querySelector("#revenue-analytics-chart"), options);
        chart.render();

        var membership_state_chart_option = {
            series: [76],
            chart: {
                type: 'radialBar',
                offsetY: -20,
                sparkline: {
                enabled: true
                }
            },
            colors: ['#04a9f5'],
            plotOptions: {
                radialBar: {
                startAngle: -95,
                endAngle: 95,
                hollow: {
                    margin: 15,
                    size: '40%',
                },
                track: {
                    background: '#04a9f525',
                    strokeWidth: '97%',
                    margin: 10
                },
                dataLabels: {
                    name: {
                    show: false
                    },
                    value: {
                    offsetY: 0,
                    fontSize: '20px'
                    }
                }
                }
            },
            grid: {
                padding: {
                top: 10
                }
            },
            stroke: {
                lineCap: 'round'
            },
            labels: ['میانگین نتایج']
        };
        var chart = new ApexCharts(document.querySelector('#membership-state-chart'), membership_state_chart_option);
        chart.render();

        var activity_line_chart_options = {
            chart: {
              type: 'line',
              height: 150,
              toolbar: {
                show: false
              }
            },
            colors: ['#1de9b6', '#1de9b6'],
            dataLabels: {
              enabled: false
            },
            legend: {
              fontFamily: `'Vazirmatn', sans-serif`,
              show: true,
              position: 'top',
            },
            markers: {
              size: 1,
              colors: ['#fff', '#fff'],
              strokeColors: ['#1de9b6', '#1de9b6'],
              strokeWidth: 1,
              shape: 'circle',
              hover: {
                size: 4
              }
            },
            fill: {
              opacity:[1,0.3]
            },
            stroke: {
              width: 3,
              curve: 'smooth',
            },
            grid: {
              show: false,
            },
            series: [
              {
                name: 'فعال',
                data: [20, 90, 65, 85, 20, 80, 30]
              },
              {
                name: 'غیرفعال',
                data: [70, 30, 40, 15, 60, 40, 95]
              }
            ],
            xaxis: {
              labels: {
                hideOverlappingLabels: true
              },
              axisBorder: {
                show: false
              },
              axisTicks: {
                show: false
              }
            }
        }
        var chart = new ApexCharts(document.querySelector("#activity-line-chart"), activity_line_chart_options);
        chart.render();
    })();
}