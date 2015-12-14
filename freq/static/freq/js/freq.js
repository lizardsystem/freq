/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false,
demandChart:false, console:false*/
/**
* Configure jQuery to send cookies with XmlHttpRequests. Necessary to access
* the Lizard API.
*
* For this to work, the API server must explicitly respond with:
* Access-Control-Allow-Credentials: true
* Access-Control-Allow-Origin: [origin_sent_in_request]
*
* Note: this must be executed before any Ajax calls!
*/

var api = 'demo.lizard.net';
$.ajaxSetup({
    // Be friends with django, add csrf token. cp-ed from
    // http://stackoverflow.com/questions/5100539/django-csrf-check-failing-with-an-ajax-post-request
    beforeSend: function(xhr, settings) {
      function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
          var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
              var cookie = $.trim(cookies[i]);
              // Does this cookie string begin with the name we want?
              if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
            }
          }
        }
        return cookieValue;
      }
      if (!(/^http:.*/.test(api) || /^https:.*/.test(api))) {
        // Only send the token to relative URLs i.e. locally.
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
     },
    timeout: 60 * 1000,
    // The docs say: default: false for same-domain requests, true for
    // cross-domain requests. So the default is good enough for us.
    // crossDomain: true,
    xhrFields: {
        // withCredentials:
        // The docs say withCredentials has no effect when same origin is used:
        // https://dvcs.w3.org/hg/xhr/raw-file/tip/Overview.html#dom-xmlhttprequest-withcredentials
        // "True when user credentials are to be included in a cross-origin request.
        // False when they are to be excluded in a cross-origin request
        // and when cookies are to be ignored in its response. Initially false."
        // So, explicitly set this to true for our purposes.
        withCredentials: true
    }
});

function loadDataError(jqXHR, textStatus, errorThrown) {
    var $error = $('<p>Fout bij het laden van de grafiekdata: ' +
        errorThrown + '</p>')
}

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
                marker.on('click', visitUrl('/timeseries/location_uuid/'
                    + locs[i][1] + '&' +  locs[i][0][1] + '&' + locs[i][0][0]));
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

function loadData(queryUrl, successFunction, requestType, data) {
    var ajaxCall = {
        url: queryUrl,
        success: successFunction,
        type: requestType == undefined ? 'GET' : requestType,
        error: loadDataError
    };
    if(data !== undefined){
        ajaxCall['data'] = data;
    }
    return $.ajax(ajaxCall);
}

function drawGraph(data, textStatus, jqXHR){
    if(data.data.length > 0) {
        console.log('data timeseries graph', data);
        nv.addGraph(function () {
            var chart = nv.models.lineChart()
                .x(function(d){return d['x'];})
                .y(function(d){return d['y'];})
                 .useInteractiveGuideline(true);

            chart.lines.dispatch.on('elementClick', function(e){
                console.log(e[0].point);
            });

            chart.xAxis
                .tickFormat(function(d) {
                  return d3.time.format('%x')(new Date(d))
            });

            //chart.x2Axis
            //    .tickFormat(function(d) {
            //      return d3.time.format('%x')(new Date(d))
            //});

            chart.yAxis
                .tickFormat(d3.format('.02f'));

            d3.select('#chart svg')
                .datum(data.data)
                //.transition().duration(500)
                .call(chart);

            d3.select('#chart > svg > g > g > .nv-focus > .nv-linesWrap' +
                ' > .nv-line')
                .on('elementClick', function(e){
                console.log(e[0].point);
            });

            nv.utils.windowResize(chart.update);

            return chart;
        });
    }
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

    //var coordinates = window.map_.center;
    //if(coordinates.length == 0){
    //    coordinates = [45, 0];
    //    zoom = 3;
    //}

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

function loadDatePicker(){
    $('.input-daterange').datepicker({
        format: 'dd-mm-yyyy',
        endDate: 'd'
    });
}

$(document).ready(
function() {
    loadMap();
    loadData('/timeseries/data', drawGraph);
    loadDatePicker();
});
