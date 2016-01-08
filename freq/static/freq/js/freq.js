/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false,
demandChart:false, console:false*/


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
        var col = false;
        if(ts){
            window.map_.min = ts.extremes.min;
            window.map_.max = ts.extremes.max;
            col = true;
            var legendLabels = JSON.parse(localStorage.getItem("legendLabels"));
            loadLegend(legendLabels);
            var colors = [];
            for(var i=0;i<legendLabels.length;i++){
                colors.push(legendLabels[i].color)
            }
            var valueRange = ts.extremes.max - ts.extremes.min;
            var colorDomain = [ts.extremes.min];
            for(var i=colors.length - 1; i > 0; i--){
                console.log(ts.extremes.min + (valueRange / i));
                colorDomain.push(ts.extremes.min + (valueRange / i))
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
            var color = col ? colorScale(ts.values[loc_uuid]) : '#1abc9c';

            if(coordinates.length > 0){
                var marker = L.marker(
                    [coordinates[1], coordinates[0]],
                    {
                        title: ts ? ts.values[loc_uuid] : locs[loc_uuid].name,
                        icon: icon(pxSize, color)
                    }
                );
                marker.on('click', visitUrl(
                        '/timeseries/location_uuid/?datatypes=locations&uuid='
                        + loc_uuid + '&x_coord=' +  coordinates[0] + '&y_coord='
                        + coordinates[1])
                );
                locationsLayer.addLayer(marker);
            }
        }
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

    window.map_.map = L.map('map').fitBounds(window.map_.bounds);
    L.tileLayer('http://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa98k8k/{z}/{x}/{y}.png ', {
        maxZoom: 17,
        tooltip: true
    }).addTo(window.map_.map);

    window.map_.locationsLayer = L.layerGroup();
    window.map_.locationsLayer.addTo(window.map_.map);

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
