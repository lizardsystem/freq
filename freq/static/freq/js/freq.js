/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false,
demandChart:false, console:false*/


var colorMap = {
  "dem-world": {
    "type": "GradientColormap",
    "free": false,
    "data": [
      [-10000, [  0,   0, 128, 255]],
      [   -20, [128, 128, 255, 255]],
      [    -5, [  0, 101,  50, 255]],
      [     0, [ 15, 126,  52, 255]],
      [     5, [ 39, 152,  58, 255]],
      [    10, [ 70, 177,  70, 255]],
      [    20, [123, 203, 107, 255]],
      [    50, [177, 228, 152, 255]],
      [   100, [228, 254, 203, 255]],
      [   200, [200, 223, 142, 255]],
      [   500, [186, 192,  92, 255]],
      [  1000, [162, 145,  51, 255]],
      [  2000, [131,  90,  20, 255]],
      [  9000, [101,  41,   0, 255]]
    ],
    "interp": [
      [-10000, 0.00],
      [   -20, 0.08],
      [    -5, 0.15],
      [     0, 0.23],
      [     5, 0.31],
      [    10, 0.38],
      [    20, 0.46],
      [    50, 0.54],
      [   100, 0.62],
      [   200, 0.69],
      [   500, 0.77],
      [  1000, 0.85],
      [  2000, 0.92],
      [  9000, 1.00]
    ]
  },
  "su-world": {
    "legend":[
      [1, "Acrisol"],
      [2, "Alisol"],
      [3, "Andosol"],
      [4, "Arenosol"],
      [5, "Anthrosol"],
      [6, "Chernozem"],
      [7, "Calcisol"],
      [8, "Cambisol"],
      [9, "Fluvisol"],
      [10, "Ferralsol"],
      [11, "Gleysol"],
      [12, "Greyzem"],
      [13, "Gypsisol"],
      [14, "Histosol"],
      [15, "Kastanozem"],
      [16, "Leptosol"],
      [17, "Luvisol"],
      [18, "Lixisol"],
      [19, "Nitisol"],
      [20, "Podzoluvisol"],
      [21, "Phaeozem"],
      [22, "Planosol"],
      [23, "Plinthosol"],
      [24, "Podzoluvisol"],
      [25, "Regosol"],
      [26, "Solonchak"],
      [27, "Solonetz"],
      [28, "Vertisol"],
      [29, "Rock outcrops"],
      [30, "Sand dunes"],
      [31, "Water bodies"],
      [32, "Urban, mining"],
      [33, "Salt flats"],
      [34, "No data"],
      [35, "Glaciers"],
      [36, "Islands"]
    ]
  },
  "whymap": {
    "legend": [
      [11, "11 - BGR - very low recharge (<2 mm year)"],
      [12, "12 - BGR - low recharge (2-20 mm/year)"],
      [13, "13 - BGR - medium recharge (20-100 mm/year)"],
      [14, "14 - BGR - high recharge (100-300 mm/year)"],
      [15, "15 - BGR - very high recharge (>300 mm/year)"],
      [22, "22 - BGR - low-very low recharge (<20 mm/year)"],
      [23, "23 - BGR - medium recharge (20-100 mm/year)"],
      [24, "24 - BGR - high recharge (100-300 mm/year)"],
      [25, "25 - BGR - very high recharge (>300 mm/year)"],
      [33, "33 - BGR - very low recharge (<100 mm/year)"],
      [34, "34 - BGR - high recharge (>100 mm/year)"],
      [88, "88 - BGR - Continuous Ice Sheet"]
    ]
  },
  "lc-world": {
    "legend": [
      [0, "0 - Water"],
      [1, "1 - Evergreen Needleleaf Forest"],
      [2, "2 - Evergreen Broadleaf Forest"],
      [3, "3 - Deciduous Needleleaf Forest"],
      [4, "4 - Deciduous Broadleaf Forest"],
      [5, "5 - Mixed Forest"],
      [6, "6 - Closed Shrublands"],
      [7, "7 - Open Shrublands"],
      [8, "8 - Woody Savannas"],
      [9, "9 - Savannas"],
      [10, "10 - Grasslands"],
      [11, "11 - Permanent Wetlands"],
      [12, "12 - Croplands"],
      [13, "13 - Urban and Built-Up"],
      [14, "14 - Cropland/Natural Vegetation Mosaic"],
      [15, "15 - Snow and Ice"],
      [16, "16 - Barren or Sparsely Vegetated"]
    ]
  }
};

L.TileLayer.BetterWMS = L.TileLayer.WMS.extend({

  onAdd: function (map) {
    // Triggered when the layer is added to a map.
    //   Register a click listener, then do all the upstream WMS things
    L.TileLayer.WMS.prototype.onAdd.call(this, map);
    map.on('click', this.getFeatureInfo, this);
  },

  onRemove: function (map) {
    // Triggered when the layer is removed from a map.
    //   Unregister a click listener, then do all the upstream WMS things
    L.TileLayer.WMS.prototype.onRemove.call(this, map);
    map.off('click', this.getFeatureInfo, this);
  },

  getFeatureInfo: function (evt) {
    var popUp = function(data){
      console.log(data);
      L.popup({ maxWidth: 800})
        .setLatLng(evt.latlng)
        .setContent(colorMap[layerName].legend[data.data[0]])
        .openOn(this._map);
    };
    // Make an AJAX request to the server and hope for the best
    console.log(evt);
    console.log(this);
    console.log(this.wmsParams.layers);
    var layerMapping = {
      
    };
    var layerName = layerMapping[this.wmsParams.layers];
    layerName = 'soil_world';
    var url = "https://demo.lizard.net/api/v2/raster-aggregates/" +
      "?agg=curve&geom=POINT(" + evt.latlng.lng + "+" + evt.latlng.lat +
      ")&srs=EPSG:4326&raster_names=" + layerName;
    console.log(url);
    loadData(url, popUp);

  }
});


L.tileLayer.betterWms = function (url, options) {
  return new L.TileLayer.BetterWMS(url, options);
};


function visitUrl(url){
    return function(){
        window.location.href = url;
    };
}

function icon(pxSize, color, innerColor){
color = color == undefined ? '#1abc9c' : color;
innerColor = innerColor == undefined ? '#fff' : innerColor;

return L.divIcon({
    className: 'nens-div-icon',
    iconAnchor: [pxSize, pxSize],
    html: '<svg height="' + (pxSize * 2 + 2) + '" width="' + (pxSize * 2 + 2)
    + '">'
    + '<circle cx="' + (pxSize + 1) + '" cy="' + (pxSize + 1)
    + '" r="' + pxSize + '" stroke="' + innerColor + '" stroke-width="1"'
    + 'fill-opacity="0.8" fill="' + color + '" />'
    + '<circle cx="' + (pxSize + 1) + '" cy="' + (pxSize + 1) + '" r="'
    + (pxSize/ 3) + '" fill-opacity="1" fill="' + innerColor + '" />'
    + '</svg>'
  });
}

function drawLocationsBoundingBox(map, locationsLayer){
  var imagesUrl = window.startpage.leafletImagesUrl;

  return function(data, textStatus, jqXHR){
    var locs = data.result.locations;
    var ts = data.result.timeseries;
    var statistic = window['map_']['dropdown_0'];
    console.log('statistic', statistic);
    var col = false;
    if(ts){
      window.map_.min = ts.extremes[statistic].min;
      window.map_.max = ts.extremes[statistic].max;
      col = true;
      var legendLabels = JSON.parse(localStorage.getItem("legendLabels"));
      loadLegend(legendLabels);
      var colors = [];
      for(var i=0;i<legendLabels.length;i++){
        colors.push(legendLabels[i].color)
      }
      var valueRange = ts.extremes[statistic].max - ts.extremes[statistic].min;
      var colorDomain = [ts.extremes[statistic].min];
      for(var i=colors.length - 1; i > 0; i--){
        console.log(ts.extremes[statistic].min + (valueRange / i));
        colorDomain.push(ts.extremes[statistic].min + (valueRange / i))
      }
      console.log('Colors', colorDomain, colors);
      locationsLayer.clearLayers();
      var colorScale = d3.scale.linear()
        .range(colors)
        .domain(colorDomain);
    }
    var pxSize = 7;
    for(var loc_uuid in locs) {
      var coordinates = locs[loc_uuid].coordinates;
      if(ts && ts.values[loc_uuid][statistic] == 'NaN'){
        var color = "#ccc";
      } else {
        var color = col ? colorScale(ts.values[loc_uuid][statistic]) : '#1abc9c';
      }
      if(coordinates.length > 0){
        var marker = L.marker(
          [coordinates[1], coordinates[0]],
          {
            title: ts ? ts.values[loc_uuid][statistic] : locs[loc_uuid].name,
            icon: icon(pxSize, color)
          }
        );
        if(window.active != "map_"){
          marker.on('click', visitUrl(
            '/timeseries/location_uuid/?datatypes=locations&uuid='
            + loc_uuid + '&x_coord=' +  coordinates[0] + '&y_coord='
            + coordinates[1])
          );
        } else {
          marker.on('click', visitUrl(
            '/map_/?datatypes=locations&uuid='
            + loc_uuid + '&x_coord=' +  coordinates[0] + '&y_coord='
            + coordinates[1])
          );
        }
        locationsLayer.addLayer(marker);
    }
  }
  if(window.active != 'map_'){
        coordinates = window.startpage.coordsSelected;
        if(coordinates.length > 0){
            var marker = L.marker(
                [coordinates[1], coordinates[0]],
                {
                    icon: icon(pxSize, color, '#444')
                }
            );
            locationsLayer.addLayer(marker);
        }
    }
  };
}


function drawGraph(){

  for(var i=0; i < 2; i++){
    nv.addGraph(function() {
      var chart = nv.models.lineChart()
        .useInteractiveGuideline(true);
      chart.xAxis
        .tickFormat(function(d) {
            return d3.time.format('%x')(new Date(d))
        });

      chart.yAxis
        .tickFormat(d3.format('.02f'));

      d3.select('#chart_' + i + ' svg')
        .datum([{
            'values': [{'y': 0, 'x': 0}, {'y': 1, 'x': 1}],
            'key': 'empty',
            'color': '#ffffff'
        }])
        .transition().duration(500)
        .call(chart);

      chart.lines.dispatch.on('elementClick', clickGraphPoint);
      nv.utils.windowResize(chart.update);

      window.charts.push(chart);

      return chart;
    });
  }
}


function clickColor(event) {
  console.log(event);
}


function loadMap() {
  function drawLocations () {
    var bounds = window.map_.map.getBounds();

    loadData(
      '/map__data/?datatypes=locations',
      drawLocationsBoundingBox(
        window.map_.map,
        window.map_.locationsLayer
      ),
      'GET',
      {bounds: JSON.stringify(bounds)}
    );
  }

  if(window.active === "map_"){
    var topography = L.tileLayer('http://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa98k8k/{z}/{x}/{y}.png ', {
      maxZoom: 17,
      tooltip: true
    });
    var satellite = L.tileLayer('http://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa79205/{z}/{x}/{y}.png ', {
      maxZoom: 17,
      tooltip: true
    });
    var neutral = L.tileLayer('http://{s}.tiles.mapbox.com/v3/nelenschuurmans.l15e647c/{z}/{x}/{y}.png ', {
      maxZoom: 17,
      tooltip: true
    });

    var aquifers = L.tileLayer.betterWms(
      'https://ggis.un-igrac.org/geoserver/tbamap2015/wms/', {
        layers: 'tbamap_2015ggis',
        maxZoom: 17,
        tooltip: true,
        format: 'image/png',
        transparent: true,
      });
    var landcover = L.tileLayer.betterWms(
      'https://raster.lizard.net/wms', {
        layers: 'world:cover',
        maxZoom: 17,
        tooltip: true,
        format: 'image/png',
        transparent: true,
        styles: "lc-world"
      });
    var WHYMAP = L.tileLayer.betterWms(
      'https://raster.lizard.net/wms', {
        layers: 'extern:ww:whymap',
        maxZoom: 17,
        tooltip: true,
        format: 'image/png',
        transparent: true,
        styles: "whymap"
      });
    var soil = L.tileLayer.betterWms(
      'https://raster.lizard.net/wms', {
        layers: 'world:soil',
        maxZoom: 17,
        tooltip: true,
        format: 'image/png',
        transparent: true,
        styles: "su-world"
      });
    var DEM = L.tileLayer.betterWms(
      'https://raster.lizard.net/wms', {
        layers: 'world:dem',
        maxZoom: 17,
        tooltip: true,
        format: 'image/png',
        transparent: true,
        styles: "dem-world",
        effects: "shade:0:0.9"
      });

    window.map_.locationsLayer = L.layerGroup();

    window.map_.map = L.map('map', {
        layers: [topography, window.map_.locationsLayer]
    }).fitBounds(window.map_.bounds);

    var baseMaps = {
      "topography": topography,
      "satellite": satellite,
      "neutral": neutral
    };

    var overlayMaps = {
      "groundwater": window.map_.locationsLayer,
      "aquifers": aquifers,
      "WHYMAP": WHYMAP,
      'landcover': landcover,
      "soil": soil,
      "DEM": DEM
    };

    L.control.layers(baseMaps, overlayMaps).addTo(window.map_.map);
  } else {
    window.map_.map = L.map('map').fitBounds(window.map_.bounds);
    L.tileLayer(
      'http://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa98k8k/{z}/{x}/{y}.png ',
      {
        maxZoom: 17,
        tooltip: true
      }
    ).addTo(window.map_.map);

    window.map_.locationsLayer = L.layerGroup();
    window.map_.locationsLayer.addTo(window.map_.map);
  }

  drawLocations ();

  window.map_.map.on('moveend', drawLocations);
}

function logData(data, textStatus, jqXHR){
  console.log(data, textStatus, jqXHR);
}


$(document).ready(
  function() {
    loadMap();
    drawGraph();
    changeGraphs()();
    //loadData('/timeseries/data', drawGraph);
  }
);
