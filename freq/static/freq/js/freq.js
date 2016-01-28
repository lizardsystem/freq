/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false,
demandChart:false, console:false*/


var colorMap = {
  "world_dem": {"legend": {}},
  "soil_world": {
    "legend":{
      1: "Acrisol",
      2: "Alisol",
      3: "Andosol",
      4: "Arenosol",
      5: "Anthrosol",
      6: "Chernozem",
      7: "Calcisol",
      8: "Cambisol",
      9: "Fluvisol",
      10: "Ferralsol",
      11:  "Gleysol",
      12:  "Greyzem",
      13:  "Gypsisol",
      14:  "Histosol",
      15:  "Kastanozem",
      16:  "Leptosol",
      17:  "Luvisol",
      18:  "Lixisol",
      19:  "Nitisol",
      20:  "Podzoluvisol",
      21:  "Phaeozem",
      22:  "Planosol",
      23:  "Plinthosol",
      24:  "Podzoluvisol",
      25:  "Regosol",
      26:  "Solonchak",
      27:  "Solonetz",
      28:  "Vertisol",
      29:  "Rock outcrops",
      30:  "Sand dunes",
      31:  "Water bodies",
      32:  "Urban, mining",
      33:  "Salt flats",
      34:  "No data",
      35:  "Glaciers",
      36:  "Islands"
    }
  },
  "whymap": {
    "legend": {
     11:  "11 - BGR - very low recharge (<2 mm year)",
     12:  "12 - BGR - low recharge (2-20 mm/year)",
     13:  "13 - BGR - medium recharge (20-100 mm/year)",
     14:  "14 - BGR - high recharge (100-300 mm/year)",
     15:  "15 - BGR - very high recharge (>300 mm/year)",
     22:  "22 - BGR - low-very low recharge (<20 mm/year)",
     23:  "23 - BGR - medium recharge (20-100 mm/year)",
     24:  "24 - BGR - high recharge (100-300 mm/year)",
     25:  "25 - BGR - very high recharge (>300 mm/year)",
     33:  "33 - BGR - very low recharge (<100 mm/year)",
     34:  "34 - BGR - high recharge (>100 mm/year)",
     88:  "88 - BGR - Continuous Ice Sheet"
    }
  },
  "landcover_world": {
    "legend": {
     0:  "0 - Water",
     1:  "1 - Evergreen Needleleaf Forest",
     2:  "2 - Evergreen Broadleaf Forest",
     3:  "3 - Deciduous Needleleaf Forest",
     4:  "4 - Deciduous Broadleaf Forest",
     5:  "5 - Mixed Forest",
     6:  "6 - Closed Shrublands",
     7:  "7 - Open Shrublands",
     8:  "8 - Woody Savannas",
     9:  "9 - Savannas",
     10:  "10 - Grasslands",
     11:  "11 - Permanent Wetlands",
     12:  "12 - Croplands",
     13:  "13 - Urban and Built-Up",
     14:  "14 - Cropland/Natural Vegetation Mosaic",
     15:  "15 - Snow and Ice",
     16:  "16 - Barren or Sparsely Vegetated"
    }
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
      if(layerName!=='world_dem'){
        var value = colorMap[layerName].legend[data.data[0]]
      } else {
        var value = "Elevation: " + data.data[0] + " (m)"
      }
      L.popup({ maxWidth: 800})
        .setLatLng(evt.latlng)
        .setContent(value)
        .openOn(window.map_.map);
    };

    var layerMapping = {
      "world:dem": "world_dem",
      "world:soil": "soil_world",
      "extern:ww:whymap": "whymap",
      "world:cover": 'landcover_world'
    };

    // Make an AJAX request to the server and hope for the best
    var layerName = layerMapping[this.wmsParams.layers];
    if (layerName!=="tbamap_2015ggis"){
      var url = "/map/feature_info/?lng=" + evt.latlng.lng + "&lat=" +
        evt.latlng.lat + "&layername=" + layerName;
      loadData(url, popUp);
    }
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


function loadMapTimeseries(uuid, name, coordinates) {
  return function(event){
    var queryUrl = '/map__data/?active=map_&name=' + name + '&uuid=' +
      uuid + '&x_coord=' +  coordinates[0] + '&y_coord=' + coordinates[1];
    loadData(queryUrl, updateGraphs);
  }
}


function drawLocationsBoundingBox(map, locationsLayer){
  return function(data, textStatus, jqXHR){
    var locs = data.result.locations;
    var ts = data.result.timeseries;
    var col = false;
    if(ts){
      try {
        var statistic = window['map_']['dropdown_0'].split(' | ')[1];
        window.map_.min = ts.extremes[statistic].min;
        window.map_.max = ts.extremes[statistic].max;
        col = true;
        var legendLabels = JSON.parse(localStorage.getItem("legendLabels"));
        loadLegend(legendLabels);
        var colors = [];
        for (var i = 0; i < legendLabels.length; i++) {
          colors.push(legendLabels[i].color)
        }
        var valueRange = ts.extremes[statistic].max - ts.extremes[statistic].min;
        var colorDomain = [ts.extremes[statistic].min];
        for (var i = colors.length - 1; i > 0; i--) {
          colorDomain.push(ts.extremes[statistic].min + (valueRange / i))
        }
        locationsLayer.clearLayers();
        var colorScale = d3.scale.linear()
          .range(colors)
          .domain(colorDomain);
      } catch(error){
        console.log(error);
        locationsLayer.clearLayers();
      }
    }
    var pxSize = 7;
    for(var loc_uuid in locs) {
      var coordinates = locs[loc_uuid].coordinates;
      var locTsExists = true;
      try {
        if(ts && ts.values[loc_uuid][statistic] == 'NaN'){
          var color = "#ccc";
        } else {
          var color = col ? colorScale(ts.values[loc_uuid][statistic]) : '#1abc9c';
        }
      } catch(error){
        var color = "#ccc"
        locTsExists = false;
      }
      if(coordinates.length > 0){
        var marker = L.marker(
          [coordinates[1], coordinates[0]],
          {
            title: ts && locTsExists ?
              Math.round(parseFloat(ts.values[loc_uuid][statistic]) * 100) / 100 :
              locs[loc_uuid].name,
            icon: icon(pxSize, color)
          }
        );
        if(window.active !== "map_"){
          marker.on('click', visitUrl(
            '/timeseries/location_uuid/?datatypes=locations&uuid='
            + loc_uuid + '&x_coord=' +  coordinates[0] + '&y_coord='
            + coordinates[1])
          );
        } else if (ts !== undefined && locTsExists){
          marker.on('click', loadMapTimeseries(
            ts.values[loc_uuid].timeseries_uuid,
            locs[loc_uuid].name,
            coordinates
          ));
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


function nvGraph(i){
  nv.addGraph(function() {
      var chart = nv.models.lineChart()
        .useInteractiveGuideline(true);
      chart.xAxis
        .tickFormat(function(d) {
            return d3.time.format('%x')(new Date(d))
        });

      chart.yAxis
        .tickFormat(d3.format('.02f'));

      chart.legend
        .maxKeyLength(60);

      d3.select('#chart_' + i + ' svg')
        .datum([{
            'values': [],
            'key': 'empty',
            'color': '#ffffff'
        }])
        .transition().duration(500)
        .call(chart);

      var exp = chart.legend.expanded();
      chart.legend.expanded(!exp);

      chart.lines.dispatch.on('elementClick', clickGraphPoint);
      nv.utils.windowResize(chart.update);

      window.charts.push(chart);

      return chart;
    });
}


function drawGraph(){
  nvGraph(0);
  nvGraph(1);
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
    var topography = L.tileLayer('https://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa98k8k/{z}/{x}/{y}.png ', {
      maxZoom: 17,
      tooltip: true
    });
    var satellite = L.tileLayer('https://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa79205/{z}/{x}/{y}.png ', {
      maxZoom: 17,
      tooltip: true
    });
    var neutral = L.tileLayer('https://{s}.tiles.mapbox.com/v3/nelenschuurmans.l15e647c/{z}/{x}/{y}.png ', {
      maxZoom: 17,
      tooltip: true
    });

    var aquifers = L.tileLayer.betterWms(
      'https://ggis.un-igrac.org/geoserver/tbamap2015/wms', {
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
    window.map_.interpolationLayer = L.tileLayer.betterWms(
      'https://raster.lizard.net/wms', {
        layers: 'world:dem',
        maxZoom: 17,
        tooltip: true,
        format: 'image/png',
        transparent: true,
        styles: "RdYlBu:-1000:1000" // TODO: = hack, improve
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
      "DEM": DEM,
      "interpolation": window.map_.interpolationLayer
    };

    window.map_.controlLayers = L.control.layers(baseMaps, overlayMaps);
    window.map_.controlLayers.addTo(window.map_.map);
  } else {
    window.map_.map = L.map('map').fitBounds(window.map_.bounds);
    L.tileLayer(
      'https://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa98k8k/{z}/{x}/{y}.png ',
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
  }
);
