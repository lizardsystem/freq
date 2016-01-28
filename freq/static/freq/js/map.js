/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false,
demandChart:false, console:false*/

function loadLegend(data){
  var dataMin = window.map_.min || 0;
  var dataMax = window.map_.max || 1;
  d3.select("svg").remove();

  var tickWidth = 6;

  var width = d3.select('#legend').node().getBoundingClientRect().width,
    height = 30;

  var svg = d3.select('#legend')
    .append('svg')
    .attr('width', width*1.1)
    .attr('height', height);

  // filters go in defs element
  var defs = svg.append("defs");

  // create filter with id #drop-shadow
  // height=130% so that the shadow is not clipped
  var filter = defs.append("filter")
    .attr("id", "drop-shadow")
    .attr("height", "130%");

  // SourceAlpha refers to opacity of graphic that this filter will be applied to
  // convolve that with a Gaussian with standard deviation 3 and store result
  // in blur
  filter.append("feGaussianBlur")
    .attr("in", "SourceAlpha")
    .attr("stdDeviation", 5)
    .attr("result", "blur");

  // translate output of Gaussian blur to the right 5px
  // store result in offsetBlur
  filter.append("feOffset")
    .attr("in", "blur")
    .attr("dx", 5)
    .attr("result", "offsetBlur");

  // overlay original SourceGraphic over translated blurred opacity by using
  // feMerge filter. Order of specifying inputs is important!
  var feMerge = filter.append("feMerge");

  feMerge.append("feMergeNode")
    .attr("in", "offsetBlur")
  feMerge.append("feMergeNode")
    .attr("in", "SourceGraphic");

  var grad = svg.append('defs')
    .append('linearGradient')
    .attr('id', 'grad')
    .attr('x1', '0%')
    .attr('x2', '100%')
    .attr('y1', '0%')
    .attr('y2', '0%');

  grad.selectAll('stop')
    .data(data)
    .enter()
    .append('stop')
    .attr('offset', function(d, i) {
      return (i / (data.length - 1)) * 100 + '%';
    })
    .style('stop-color', function(d) {
      return d.color;
    })
    .style('stop-opacity', 1);

  svg.append('rect')
    .attr('x', 0)
    .attr('y', height/2)
    .attr('width', width)
    .attr('height', height)
    .attr('fill', 'url(#grad)');

  var axisScale = d3.scale.linear()
    .domain([dataMin, dataMax])
    .range([0,width]);

  var xAxis = d3.svg.axis()
    .scale(axisScale)
    .tickSize(-height).tickSubdivide(true)
    .orient('top');

  svg.append('g')
    .attr("class", "x axis")
    .attr("transform", "translate(0," + (height/2) + ")")
    .call(xAxis);

  var g = svg.append('g')
    .selectAll('.label')
    .data(data)
    .enter();

  g.append('rect')
    .attr('opacity', function(d) {
      return '0';
    })
    .attr('x',function(d,i){
      return xPos(i)
      })
    .attr('width',function(d,i){
      return width / (data.length - 1)
      })
    .attr('y',function(d,i){
      return height / 2;
      })
    .attr('height',function(d,i){
      return height / 2;
      })
    .on('click', function(d, i){
      var firstPart = data.slice(0, i+1);
      firstPart.push({color: '#fff'});
      var secondPart = data.slice(i+1);
      data = firstPart.concat(secondPart);
      var data2 = $.extend(true, [], data);
      localStorage.setItem("legendLabels", JSON.stringify(data2));
      loadLegend(data2);
    });

  g.append('line')
    .style('stroke', function(d) {
      return '#16a085';
    })
    .style('stroke-width', 12)
    .attr('x1',function(d,i){
      return xPos2(i) - 1
    })
    .attr('x2',function(d,i){
      return xPos2(i)
    })
    .attr('y1',function(d,i){
      return height / 2 - 1;
    })
     .attr('y2',function(d,i){
      return height + 4
    });
      //.style("filter", "url(#drop-shadow)");

  g.append('line')
    .style('stroke', function(d) {
      return '#e7ffe9';
    })
    .style('stroke-width', 8)
    .attr('x1',function(d,i){
      return xPos2(i) - 1
    })
    .attr('x2',function(d,i){
      return xPos2(i) - 1
    })
    .attr('y1',function(d,i){
      return height / 2  ;
    })
     .attr('y2',function(d,i){
      return height  - 2
    });

  var doubleClicked = 0;

  g.append('line')
    .style('stroke', function(d) {
      return d.color;
    })
    .style('stroke-width', 6)
    .attr('x1',function(d,i){
      return xPos2(i)
    })
    .attr('x2',function(d,i){
      return xPos2(i)
    })
    .attr('y1',function(d,i){
      return height / 2 + 2;
    })
     .attr('y2',function(d,i){
      return height - 2
    })
    .on('dblclick', function(d, i){
      doubleClicked = true;
      d3.event.stopPropagation();
      if(data.length>2){
        data.splice(i, 1);
        var data2 = $.extend(true, [], data);
        localStorage.setItem("legendLabels", JSON.stringify(data2));
        loadLegend(data2);
      }
      setTimeout(function(){doubleClicked = false;},1000)
    })
    .on('click', function(d, i){
      setTimeout(function(){
        if(!doubleClicked){
          var x = $('.colorpick-min');
          x.colorpicker({color:$.extend(true, [], data)[i].color})
           .colorpicker('show');
          x.colorpicker().on('changeColor.colorpicker', function(event){
            var newColor = event.color.toHex();
            data[i].color =  newColor;
            var data2 = $.extend(true, [], data);
            localStorage.setItem("legendLabels", JSON.stringify(data2));
            loadLegend(data2);
          });
        }
      }, 250);
    });

  function xPos2(i) {
      if(i==data.length - 1){
          return xPos(i) - tickWidth / 2
      } else if(i==0) {
          return tickWidth / 2;
      } else {
          return xPos(i)
      }

  }

  function xPos(i){
    return (width / (data.length - 1)) * i;
  }
}


function extraUpdate(data){
  // First update the date picker with the first and last dates found
  var graphs = data.graphs;
  if (graphs !== undefined){
    $('#chart_0').removeClass('hidden');
    console.log('graphs[0].measurement_point', graphs[0].measurement_point);
    $("#measurement_point")
      .removeClass('hidden')
      .text(graphs[0].measurement_point);
  }
  var result = data.result;
  if(result !== undefined){
    var timeseries = result.timeseries;
    var datePickerDates = datePickerValue();
    if (timeseries !== undefined && timeseries.dates !== undefined) {
      var startDate =  timeseries.dates.start || datePickerDates['start'];
      var endDate = timeseries.dates.end || datePickerDates['end'];
      console.log(timeseries.dates.startString, datePickerDates['start']);
      setDate(startDate, endDate);
    }
    drawLocationsBoundingBox(window.map_.map, window.map_.locationsLayer)(data);
    resetInterpolation()
  }
  spinnerClear();
}

function loadTimeseries(event) {
  //var zoomLevel = window.map_.map.getZoom();
  //if (zoomLevel > 5) {
    spinnerShow();
    var queryUrl = '/' + window.active + '_data/';
    var bounds = window.map_.map.getBounds();
    loadData(queryUrl, updateGraphs, 'GET', {
      bounds: JSON.stringify(bounds)});
  //}
}

function spinnerShow(){
  var map = $('#map');
  var height = map.height() * -0.55 + "px";
  var width = map.width() * 0.49 + "px";
  $('#wait-spinner')
    .css('margin-top', height)
    .css('margin-left', width)
    .removeClass('hidden');
}

function spinnerClear(){
  $('#wait-spinner').addClass('hidden');
}


function resetInterpolation(){
  var layers = 'world:dem';
  var bbox = window.map_.map.getBounds().toBBoxString();
  console.log(bbox, 'should look like: 2.804441731588852,51.1097471300875,' +
    '7.69580509387341,53.039276641988344');
  var url = "/map/interpolation_limits/?layers=" + layers + "&bbox=" + bbox;
  loadData(url, function(data){
    var lowestValue = data[0][0];
    var highestValue = data[0][1];
    window.map_.controlLayers.removeLayer(window.map_.interpolationLayer);
    window.map_.map.removeLayer(window.map_.interpolationLayer);
    window.map_.interpolationLayer = L.tileLayer.betterWms(
      'https://raster.lizard.net/wms', {
        layers: 'world:dem',
        maxZoom: 17,
        tooltip: true,
        format: 'image/png',
        transparent: true,
        styles: "RdYlBu:" + lowestValue + ":" + highestValue,
      }
    );
    window.map_.controlLayers.addOverlay(
      window.map_.interpolationLayer, 'interpolation');
    window.map_.interpolationLayer.addTo(window.map_.map);
  });
}


$(document).ready(
  function() {
    var defaultLabels = [{
      color: '#2ecc71'
    }, {
      color: '#1abc9c'
    }, {
      color: '#3498db'
    }];
    var legendLabels = JSON.parse(localStorage.getItem("legendLabels"));
    legendLabels = legendLabels || defaultLabels;
    localStorage.setItem("legendLabels", JSON.stringify(legendLabels));
    loadLegend(legendLabels);
    window.map_.map.on('moveend', loadTimeseries);
  }
);