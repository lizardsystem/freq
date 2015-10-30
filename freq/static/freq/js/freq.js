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

    function drawLocationsBoundingBox(map){
        return function(data, textStatus, jqXHR){
            var locs = data['locations']
            for(var i=0; i<locs.length; i++){
                var coordinates = [locs[i][0][1], locs[i][0][0]];
                var marker = L.marker(
                    coordinates,
                    {
                        title: locs[i][2]
                    });
                marker.on('click', visitUrl('/timeseries/' + locs[i][1]));
                marker.addTo(map);
            }
        };
    }

    function loadData(queryUrl, successFunction, data, requestType) {
        var ajaxCall = {
            url: queryUrl,
            success: successFunction,
            type: requestType == undefined ? 'POST' : 'GET',
            error: loadDataError,
            data: data
        };
        if(data !== undefined){
            ajaxCall['data'] = data
        }
        return $.ajax(ajaxCall);
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
            loadData('/locations/', drawLocationsBoundingBox(map), bbox);
        }

        var map = L.map('map').setView([45, 0], 3);
        L.tileLayer('http://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa98k8k/{z}/{x}/{y}.png ', {
            maxZoom: 18,
            tooltip: true
        }).addTo(map);
        drawLocations ();
        console.log('loaded_map');

        map.on('moveend', drawLocations);
    }

    $(document).ready(
        function() {
            loadMap();
        });
})(jQuery);