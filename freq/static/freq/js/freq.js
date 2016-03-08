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
      11: "Major Groundwater basin: very low recharge",
      12: "Major Groundwater basin: low recharge",
      13: "Major Groundwater basin: medium recharge",
      14: "Major Groundwater basin: high recharge",
      15: "Major Groundwater basin: very high recharge",
      22: "Complex hydrogeological structure: low recharge",
      23: "Complex hydrogeological structure: medium recharge",
      24: "Complex hydrogeological structure: high recharge",
      25: "Complex hydrogeological structure: very high recharge",
      33: "Local and shallow aquifers: very low recharge",
      34: "Local and shallow aquifers: high recharge",
      88: "Contineous Ice sheet"
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


L.Control.OpacityLayers = L.Control.Layers.extend({

	_addItem: function (obj) {
		var label = document.createElement('label'),
		    input,
		    checked = this._map.hasLayer(obj.layer);

		if (obj.overlay) {
			input = document.createElement('input');
			input.type = 'checkbox';
			input.className = 'leaflet-control-layers-selector';
			input.defaultChecked = checked;

      if(obj.name!=='groundwater') {
        /*
          Following code is taken from:
          Leaflet.OpacityControls, a plugin for adjusting the opacity of a Leaflet map.
          (c) 2013, Jared Dominguez
          (c) 2013, LizardTech
          https://github.com/lizardtechblog/Leaflet.OpacityControls
        */
        var opacity_slider_div = L.DomUtil.create('div', 'opacity_slider_control');

        $(opacity_slider_div)
          .slider({
            range: "min",
            min: 0,
            max: 100,
            value: 60,
            step: 10,
            start: function (event, ui) {
              console.log(event);
              //When moving the slider, disable panning.
              window.map_.map.dragging.disable();
              window.map_.map.once('mousedown', function (e) {
                window.map_.map.dragging.enable();
              });
            },
            slide: function (event, ui) {
              var slider_value = ui.value / 100;
              obj.layer.setOpacity(slider_value);
            }
          });
      }
		} else {
			input = this._createRadioElement('leaflet-base-layers', checked);
		}

		input.layerId = L.stamp(obj.layer);

		L.DomEvent.on(input, 'click', this._onInputClick, this);

		var name = document.createElement('span');
		name.innerHTML = ' ' + obj.name;

		label.appendChild(input);
		label.appendChild(name);
    if (obj.overlay && obj.name!=='groundwater') {
      label.appendChild(opacity_slider_div);
    }
		var container = obj.overlay ? this._overlaysList : this._baseLayersList;
		container.appendChild(label);

		return label;
	}
});

L.control.opacityLayers = function (baseLayers, overlays, options) {
	return new L.Control.OpacityLayers(baseLayers, overlays, options);
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
    var popUp = function(data) {
      if(layerName === 'tbamap_2015ggis') {
        var value = data.data
      } else if((layerName!=='world_dem' && layerName.indexOf('igrac') == -1)){
        var value = colorMap[layerName].legend[data.data[0]]
      } else {
        var value = data.data[0] + " (m)"
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
      "world:cover": 'landcover_world',
      "tbamap_2015ggis": "tbamap_2015ggis"
    };

    var orgCode = window.map_.organisationWMSLayers[$('.organisation').text().trim()];
    layerMapping[orgCode] = orgCode;
    // Make an AJAX request to the server and hope for the best
    var layerName = layerMapping[this.wmsParams.layers];
    console.log(orgCode, layerName, layerMapping, this.wmsParams.layers);

    if (layerName!=="tbamap_2015ggis"){
      var url = "/map/feature_info/?lng=" + evt.latlng.lng + "&lat=" +
        evt.latlng.lat + "&layername=" + layerName;
    } else {
      var url = this.getFeatureInfoUrl(evt.latlng);
      console.log(url);
    }
    loadData(url, popUp);
  },

  getFeatureInfoUrl: function (latlng) {
    // Construct a GetFeatureInfo request URL given a point
    var point = this._map.latLngToContainerPoint(latlng, this._map.getZoom()),
      size = this._map.getSize(),

      params = {
        version: this.wmsParams.version,
        format: this.wmsParams.format,
        bbox: this._map.getBounds().toBBoxString(),
        height: size.y,
        width: size.x,
        layers: this.wmsParams.layers,
        query_layers: this.wmsParams.layers,
      };

    params[params.version === '1.3.0' ? 'i' : 'x'] = point.x;
    params[params.version === '1.3.0' ? 'j' : 'y'] = point.y;

    return "/map/feature_info/" +
      L.Util.getParamString(params, this._url, true);
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
        var color = "#ccc";
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
        .useInteractiveGuideline(true)
        .margin({top: 20, right: 35, bottom: 30, left: 70});
      chart.xAxis
        .tickFormat(function(d) {
            return d3.time.format('%d-%m-%Y')(new Date(d))
        });

      chart.yAxis
        .axisLabel('Groundwaterlevel ' + window.chart.reference + ' (m)')
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


function drawLocations () {
    var bounds = window.map_.map.getBounds();
    var url = window.active === 'map_' ?
      '/map__data/?' :
      '/map__data/?datatypes=locations';

    loadData(
      url,
      drawLocationsBoundingBox(
        window.map_.map,
        window.map_.locationsLayer
      ),
      'GET',
      {bounds: JSON.stringify(bounds)}
    );
  }

function loadMap() {
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

    var layers = window.map_.organisationWMSLayers[$('.organisation').text().trim()];

    window.map_.interpolationLayer = L.tileLayer.betterWms(
      'https://raster.staging.lizard.net/wms', {
        layers: layers,
        maxZoom: 17,
        tooltip: true,
        format: 'image/png',
        transparent: true,
        styles: "RdYlBu:-1000:1000"
      });

    window.map_.locationsLayer = L.layerGroup();

    window.map_.map = L.map('map', {
      layers: [topography, window.map_.locationsLayer],
      minZoom: 6
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
    };

    var organisation = $('.organisation').text().trim()
    if (organisation !== 'Public'){
      overlayMaps['interpolation BGS'] = window.map_.interpolationLayer
    }

    // create the control

    window.map_.controlLayers = L.control.opacityLayers(baseMaps, overlayMaps);
    window.map_.controlLayers.addTo(window.map_.map);

    if (organisation !== 'Public') {
      var rescaleControl = L.control({position: 'topright'});
      rescaleControl.onAdd = function (map) {
        var div = L.DomUtil.create('div', 'rescale-control');

        div.innerHTML = '<button id="rescale-button" ' +
          'onclick="resetInterpolation(event);" title="rescale interpolation"' +
          ' class="btn btn-sm"> <div class="glyphicon' +
          ' glyphicon-resize-full"></div></button>';
        return div;
      };
      rescaleControl.addTo(window.map_.map);
    }
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

var _gauges = _gauges || [];
(function() {
 var t   = document.createElement('script');
 t.type  = 'text/javascript';
 t.async = true;
 t.id    = 'gauges-tracker';
 t.setAttribute('data-site-id', '56ded50dbb922a528c003437');
 t.setAttribute('data-track-path', 'https://track.gaug.es/track.gif (35b)');
 t.src = 'https://d36ee2fcip1434.cloudfront.net/track.js';
 var s = document.getElementsByTagName('script')[0];
 s.parentNode.insertBefore(t, s);
})();

$(document).ready(
  function() {
    loadMap();
    drawGraph();
    changeGraphs()();
  }
);
