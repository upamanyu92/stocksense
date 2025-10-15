// Real-time charting functionality for StockSense
// Uses Chart.js for live updating charts

class RealtimeChart {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      console.error(`Canvas element ${canvasId} not found`);
      return;
    }
    
    this.ctx = this.canvas.getContext('2d');
    this.maxDataPoints = options.maxDataPoints || 20;
    this.chart = null;
    this.initChart(options);
  }
  
  initChart(options) {
    const defaultOptions = {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: options.label || 'Stock Price',
          data: [],
          borderColor: 'rgba(0, 212, 255, 1)',
          backgroundColor: 'rgba(0, 212, 255, 0.1)',
          borderWidth: 2,
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 750
        },
        scales: {
          y: {
            beginAtZero: false,
            ticks: {
              color: 'rgba(224, 224, 224, 0.8)'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.05)'
            }
          },
          x: {
            ticks: {
              color: 'rgba(224, 224, 224, 0.8)'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.05)'
            }
          }
        },
        plugins: {
          legend: {
            labels: {
              color: 'rgba(224, 224, 224, 1)'
            }
          }
        }
      }
    };
    
    this.chart = new Chart(this.ctx, defaultOptions);
  }
  
  addDataPoint(label, value) {
    if (!this.chart) return;
    
    this.chart.data.labels.push(label);
    this.chart.data.datasets[0].data.push(value);
    
    // Remove old data points if exceeding max
    if (this.chart.data.labels.length > this.maxDataPoints) {
      this.chart.data.labels.shift();
      this.chart.data.datasets[0].data.shift();
    }
    
    this.chart.update();
  }
  
  updateLastPoint(value) {
    if (!this.chart || this.chart.data.datasets[0].data.length === 0) {
      return;
    }
    
    const dataLength = this.chart.data.datasets[0].data.length;
    this.chart.data.datasets[0].data[dataLength - 1] = value;
    this.chart.update();
  }
  
  clearChart() {
    if (!this.chart) return;
    
    this.chart.data.labels = [];
    this.chart.data.datasets[0].data = [];
    this.chart.update();
  }
  
  setLabel(label) {
    if (!this.chart) return;
    
    this.chart.data.datasets[0].label = label;
    this.chart.update();
  }
}

// Multi-line chart for comparing stocks
class MultiStockChart {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      console.error(`Canvas element ${canvasId} not found`);
      return;
    }
    
    this.ctx = this.canvas.getContext('2d');
    this.maxDataPoints = options.maxDataPoints || 20;
    this.chart = null;
    this.colors = [
      'rgba(0, 212, 255, 1)',
      'rgba(0, 255, 135, 1)',
      'rgba(255, 0, 110, 1)',
      'rgba(255, 170, 0, 1)',
      'rgba(138, 43, 226, 1)'
    ];
    this.initChart(options);
  }
  
  initChart(options) {
    const defaultOptions = {
      type: 'line',
      data: {
        labels: [],
        datasets: []
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 750
        },
        scales: {
          y: {
            beginAtZero: false,
            ticks: {
              color: 'rgba(224, 224, 224, 0.8)'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.05)'
            }
          },
          x: {
            ticks: {
              color: 'rgba(224, 224, 224, 0.8)'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.05)'
            }
          }
        },
        plugins: {
          legend: {
            labels: {
              color: 'rgba(224, 224, 224, 1)'
            }
          }
        }
      }
    };
    
    this.chart = new Chart(this.ctx, defaultOptions);
  }
  
  addStock(symbol, label) {
    if (!this.chart) return;
    
    const colorIndex = this.chart.data.datasets.length % this.colors.length;
    const color = this.colors[colorIndex];
    
    this.chart.data.datasets.push({
      label: label || symbol,
      data: [],
      borderColor: color,
      backgroundColor: color.replace('1)', '0.1)'),
      borderWidth: 2,
      tension: 0.4,
      fill: false
    });
    
    this.chart.update();
  }
  
  removeStock(symbol) {
    if (!this.chart) return;
    
    const index = this.chart.data.datasets.findIndex(ds => ds.label === symbol);
    if (index !== -1) {
      this.chart.data.datasets.splice(index, 1);
      this.chart.update();
    }
  }
  
  addDataPoint(symbol, label, value) {
    if (!this.chart) return;
    
    // Add label if not exists
    if (!this.chart.data.labels.includes(label)) {
      this.chart.data.labels.push(label);
      
      // Remove old labels if exceeding max
      if (this.chart.data.labels.length > this.maxDataPoints) {
        this.chart.data.labels.shift();
        // Also remove first data point from all datasets
        this.chart.data.datasets.forEach(ds => {
          if (ds.data.length > 0) {
            ds.data.shift();
          }
        });
      }
    }
    
    // Find dataset for this symbol
    const dataset = this.chart.data.datasets.find(ds => ds.label === symbol);
    if (dataset) {
      dataset.data.push(value);
    }
    
    this.chart.update();
  }
  
  clearChart() {
    if (!this.chart) return;
    
    this.chart.data.labels = [];
    this.chart.data.datasets.forEach(ds => {
      ds.data = [];
    });
    this.chart.update();
  }
}

// Export for use in dashboard
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { RealtimeChart, MultiStockChart };
}
