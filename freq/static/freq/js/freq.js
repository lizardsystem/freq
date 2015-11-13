+/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false,
demandChart:false, console:false*/
(function($) {
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

    function drawLocationsBoundingBox(map, locationsLayer){
        var imagesUrl = window.startpage.leafletImagesUrl;
        var greenIcon = L.icon({
            iconUrl: imagesUrl + 'marker-icon.png',
            shadowUrl: imagesUrl + 'marker-shadow-new.png',

            iconSize:     [16, 16], // size of the icon
            shadowSize:   [40, 40], // size of the shadow
            iconAnchor:   [8, 8], // point of the icon which will
            // correspond to marker's location
            shadowAnchor: [16, 16],  // the same for the shadow
            popupAnchor:  [-3, -76] // point from which the popup should open relative to the iconAnchor
        });
        var selectedIcon = L.icon({
            iconUrl: imagesUrl + 'marker-selected.png',
            shadowUrl: imagesUrl + 'marker-shadow.png',

            iconSize:     [16, 16], // size of the icon
            shadowSize:   [40, 40], // size of the shadow
            iconAnchor:   [8, 8], // point of the icon which will
            // correspond to marker's location
            shadowAnchor: [11, 20],  // the same for the shadow
            popupAnchor:  [-3, -76] // point from which the popup should open relative to the iconAnchor
        });

        return function(data, textStatus, jqXHR){
            var locationError = data['error'];
            if(locationError !=="" ){
                $('#error-well').removeClass('hidden')
            } else {
                var locs = data['locations'];
                locationsLayer.clearLayers();
                for(var i=0; i<locs.length; i++){
                    var coordinates = [locs[i][0][1], locs[i][0][0]];
                    var marker = L.marker(
                        coordinates,
                        {
                            icon: greenIcon,
                            title: locs[i][2],
                            opacity: 0.6
                        });
                    marker.on('click', visitUrl('/timeseries/location_uuid/' + locs[i][1] + '&' +  locs[i][0][1] + '&' + locs[i][0][0]));
                    locationsLayer.addLayer(marker);
                }
                coordinates = JSON.parse(window.startpage.coordsSelected);
                if(coordinates.length > 0){
                    var marker = L.marker(
                        coordinates,
                        {
                            icon: selectedIcon
                        }
                    );
                    locationsLayer.addLayer(marker);
                }
            }
        };
    }

    function loadData(queryUrl, successFunction, requestType, data) {
        var ajaxCall = {
            url: queryUrl,
            success: successFunction,
            type: requestType == undefined ? 'GET' : 'POST',
            error: loadDataError
        };
        if(data !== undefined){
            ajaxCall['data'] = data
        }
        return $.ajax(ajaxCall);
    }

    function drawGraph(data, textStatus, jqXHR){
        console.log(data, textStatus, jqXHR);
        if(data['data'].length > 0) {
            nv.addGraph(function () {
                var chart = nv.models.lineChart()
                    .x(function(d){return d['x'];})
                    .y(function(d){return d['y'];})
                    .useInteractiveGuideline(true)

                chart.xAxis
                    .axisLabel('Date')
                    .tickFormat(function(d) {
                      return d3.time.format('%x')(new Date(d))
                });

                chart.yAxis
                    .axisLabel('Waterlevel (m)')
                    .tickFormat(d3.format('.02f'));

                chart.lines.dispatch.on('elementClick', function(e){
                    console.log(e[0].point);
                });

                d3.select('#chart svg')
                    .datum(data.data)
                    //.transition().duration(500)
                    .call(chart);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        }
    }

    function loadMap() {
        function drawLocations () {
            var bounds = map.getBounds();
            var bbox = {
                SWlat: bounds._southWest.lat,
                SWlng: bounds._southWest.lng,
                NElat: bounds._northEast.lat,
                NElng: bounds._northEast.lng
            };
            loadData('/locations/', drawLocationsBoundingBox(map, locationsLayer), 'POST', bbox);
        }
        var coordinates = JSON.parse(window.startpage.coordsSelected);
        var zoom = 10;
        if(coordinates.length == 0){
            coordinates = [45, 0];
            zoom = 3;
        }

        var map = L.map('map').setView(coordinates, zoom);
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
        });
})(jQuery);