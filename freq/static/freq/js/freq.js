+/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false,
demandChart:false, console:false*/
(function($) {
    var loadMap = function() {
        var map = L.map('map').setView([35, 0], 1);
        L.tileLayer('http://{s}.tiles.mapbox.com/v3/nelenschuurmans.iaa98k8k/{z}/{x}/{y}.png ', {
            maxZoom: 18,
            tooltip: true
        }).addTo(map);
        //var marker1 = L.marker(
        //    [51.4478, 4.2312],
        //    {
        //        title: 'Kreekraksluizen',
        //        opacity: 0.7
        //    }
        //).addTo(map);
    };
    $(document).ready(
        function() {
            loadMap();
        });
})(jQuery);