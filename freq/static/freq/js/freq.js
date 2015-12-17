/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false,
demandChart:false, console:false*/

var charts = [];


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
        console.log(data);
        var locs = data.result.locations;
        console.log('Time series:', data.result.timeseries);
        data.values = {'min_total':0.5, 'max_total':2.5};
        var minValue = data.values['min_total'];
        var maxValue = data.values['max_total'];
        var legendLabels = JSON.parse(localStorage.getItem("legendLabels"));
        var colors = [];
        for(var i=0;i<legendLabels.length;i++){
            colors.push(legendLabels[i].color)
        }
        locationsLayer.clearLayers();
        var colorScale = d3.scale.linear()
            .range(colors)
            .domain([minValue, maxValue]);
        var pxSize = 7;
        var color = '#1abc9c';
        for(var i=0; i<locs.length; i++) {
            var coordinates = [locs[i][0][1], locs[i][0][0]];

            if(coordinates.length > 0){
                var marker = L.marker(
                    coordinates,
                    {
                        icon: icon(pxSize, color)
                    }
                );
                marker.on('click', visitUrl('/timeseries/location_uuid/?uuid='
                    + locs[i][1] + '&x_coord=' +  locs[i][0][1] + '&y_coord='
                    + locs[i][0][0]));
                locationsLayer.addLayer(marker);
            }
        }
        coordinates = window.startpage.coordsSelected;
        if(coordinates.length > 0){
            var marker = L.marker(
                coordinates,
                {
                    icon: icon(pxSize, color, '#444')
                }
            );
            locationsLayer.addLayer(marker);
        }
    };
}


function drawGraph(data, textStatus, jqXHR){
    //if(data.data.length > 0) {
        console.log(data.data);
        nv.addGraph(function() {
          var chart = nv.models.lineChart()
            .useInteractiveGuideline(true)
            ;

          chart.xAxis
            .axisLabel('Time (ms)')
            .tickFormat(d3.format(',r'))
            ;

          chart.yAxis
            .axisLabel('Voltage (v)')
            .tickFormat(d3.format('.02f'))
            ;

          d3.select('#chart svg')
            .datum(data.data)
            .transition().duration(500)
            .call(chart)
            ;

          nv.utils.windowResize(chart.update);

          return chart;
        });

        //for(var i=0; i < data.data.length; i++){
        //    console.log(i, data.data[0])
        //    nv.addGraph(function () {
        //        var chart = nv.models.lineChart()
        //            .x(function(d){return d['x'];})
        //            .y(function(d){return d['y'];})
        //             .useInteractiveGuideline(true);
        //
        //        chart.lines.dispatch.on('elementClick', clickGraphPoint);
        //
        //        chart.xAxis
        //            .tickFormat(function(d) {
        //              return d3.time.format('%x')(new Date(d))
        //        });
        //
        //        chart.yAxis
        //            .tickFormat(d3.format('.02f'));
        //
        //        d3.select('#chart_' + i + ' > svg')
        //            .datum(data.data[i])
        //            //.transition().duration(500)
        //            .call(chart);
        //
        //        //d3.select('#chart > svg > g > g > .nv-focus > .nv-linesWrap' +
        //        //    ' > .nv-line')
        //        //    .on('elementClick', clickGraphPoint); // TODO: check of dit klopt
        //
        //        nv.utils.windowResize(chart.update);
        //
        //        //charts.push(chart);
        //
        //        return chart;
        //    });
        //}
    //}
}

function loadMap() {
    function drawLocations () {
        var bounds = map.getBounds();
        var bbox = {
            coordinates: JSON.stringify({
                SWlat: bounds._southWest.lat,
                SWlng: bounds._southWest.lng,
                NElat: bounds._northEast.lat,
                NElng: bounds._northEast.lng
            })
        };
        loadData('/bbox/?datatypes=locations', drawLocationsBoundingBox(map, locationsLayer),
            'GET', bbox);
    }

    var map = L.map('map').setView(window.map_.center, window.map_.zoom);
    L.tileLayer('http://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa98k8k/{z}/{x}/{y}.png ', {
        maxZoom: 18,
        tooltip: true
    }).addTo(map);

    var locationsLayer = L.layerGroup();
    locationsLayer.addTo(map);

    drawLocations ();

    map.on('moveend', drawLocations);
}

function logData(data, textStatus, jqXHR){
    console.log(data, textStatus, jqXHR);
}


$(document).ready(
    function() {
        loadMap();
        loadData('/timeseries/data', drawGraph);
    }
);
