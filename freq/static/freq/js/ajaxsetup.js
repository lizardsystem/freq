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
      waitSpinnerShow();
      if (!(/^http:.*/.test(api) || /^https:.*/.test(api))) {
        // Only send the token to relative URLs i.e. locally.
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
     },
    complete: waitSpinnerClear,
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


var spinnerCount = 0;


function waitSpinnerShow(){
  spinnerCount += 1;
  if (spinnerCount === 1){
    var baseContainer = $("#base-container");
    var width, height;
    if (baseContainer.length){
      height = (baseContainer.height() - 200) * -0.55;
      width = (baseContainer.width() - 150) * 0.49 + "px";
    } else {
      var map = $('#map');
      height = map.height() * -0.55;
      width = map.width() * 0.49 + "px";
    }
    $('#wait-spinner')
      .css('margin-top', height + "px")
      .css('margin-bottom', -1 * height + 10 + "px")
      .css('margin-left', width)
      .removeClass('hidden');
  }

}


function waitSpinnerClear(){
  spinnerCount -= 1;
  if (spinnerCount <= 0){
    $('#wait-spinner').addClass('hidden');
  }
}


function loadDataError(jqXHR, textStatus, errorThrown) {
    var $error = $('<p>Fout bij het laden van de grafiekdata: ' +
        errorThrown + '</p>')
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
