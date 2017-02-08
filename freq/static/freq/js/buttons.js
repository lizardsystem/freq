/*global $:false, jQuery:false, moment:false, ko:false, fillChart:false, */


function datePickerValue() {
    return {
        start: $('#date_picker_start').val(),
        end: $('#date_picker_end').val()
    };
}


function spinnerValue(i) {
    return function(){
        return {
            value: $('#spinner_' + i).val()
        };
    };
}


function nextTabActive(){
    var nextTab = {
        trend_detection: ['periodic_fluctuations'],
        periodic_fluctuations: ['autoregressive'],
        autoregressive: ['additive', 'frequency']
    }[window.active];
    if(nextTab != undefined){
      for(var i = 0; i < nextTab.length; i++){
        $('[aria-controls="' + nextTab[i] + '"]').removeClass('disabled');
        $('[aria-controls="' + nextTab[i] + '"] > a').attr('href', '/' + nextTab[i]);
      }
    }
}

function changeGraphs(buttonType, altValue, changeTabs){
    return function(value){
        spinnerShow();
        if (changeTabs) {
            nextTabActive()
        }
        if (altValue !==undefined) { value = altValue(); }
        if (value !== undefined){
            window[window.active][buttonType] = value.value;
        }
        var val = JSON.stringify(value);
        var queryUrl = '/' + window.active + '_data/?button=' + buttonType +
            '&value=' + val;
        loadData(queryUrl, updateGraphs)
    };
}

window.charts = [];


function extraUpdate(data){
  if(data.error !== undefined){
    $("#graph-error-well")
      .removeClass('hidden')
      .text(data.error);
  }
  if(data.graphs[0].data[0].values.length){
    $("#error-well")
        .addClass("hidden")
        .text("");
  }
  window.map_.locationsLayer.clearLayers();
  drawLocations();
}


function lastUpdate(data){};

function updateGraphs(data){
  extraUpdate(data);
  var graphs = data.graphs;
  if(graphs !== undefined){
    var info = data.statistics;
    if(info) {
        $(".statistics_1").addClass('hidden');
        for(var i=0; i < info.length; i++){
            $(".statistics_" + i).removeClass('hidden');
            $(".statistics-well_" + i).text(info[i]);
        }
    }
    var chart = $('#chart_1');
    var chart0 = $('#chart_0');
    if(graphs.length == 2){
      var height = chart0.height();
      var width = chart0.width();
      $('#chart_1 > svg > g').css('height', height).css('width', width)
        .css('margin-top', '-50px');
      chart.removeClass('hidden').addClass('show');
      chart0.removeClass('hidden').addClass('show');
    } else if(graphs.length == 1) {
      chart.removeClass('show').addClass('hidden');
      chart0.removeClass('hidden').addClass('show');
    }
    if(window.active == 'periodic_fluctuations' ||
       window.active == 'autoregressive'){
        window.charts[0].xAxis.tickFormat(function(d) {return d});
    }
    for(var i=0; i < graphs.length; i++ ){
        var graph = graphs[i];
        window.charts[i].yAxis
            .axisLabel(graphYAxis(i));
        d3.select(graph.name)
            .datum(graph.data)
            .call(window.charts[i]);
    }
    spinnerClear();
  }
}


var spinnerCount = 0;

function spinnerShow(){
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

function spinnerClear(){
  spinnerCount -= 1;
  if (spinnerCount === 0){
    $('#wait-spinner').addClass('hidden');
  }
}

function setDate(startDate, endDate){
    $('#date_picker_start').datepicker('setDate', startDate);
    $('#date_picker_end').datepicker('setDate', endDate);
}


function loadDatePicker(){
    var changeDate = function(value) {
        var dates = datePickerValue();
        if (window.startpage.startDate !== dates.start || window.startpage.endDate !== dates.end){
            window.startpage.startDate = dates.start;
            window.startpage.endDate = dates.end;
            changeGraphs('datepicker', datePickerValue)(value);
        }
    };
    var daterange = $('.input-daterange');
    daterange.datepicker({
        format: 'dd-mm-yyyy',
        startDate: '1-1-1930',
        endDate: 'd',
        viewMode: 'years'
    });
    setDate(window.startpage.startDate, window.startpage.endDate);
    daterange.change(changeDate);
}


function loadSpinner(range){
    for(var i=0; i < range; i++){
        $('#spinner_' + i).spinner().change(
          changeGraphs('spinner_' + i, spinnerValue(i), true));
    }
    // hier setTimeout(function() gebruiken! en even checken of
    // het direct werkt. Anders boolean zetten die daarbuiten
    // ook gezet wordt.
}


function clickDropDown(dropdown_id, option_id){
  var oldSelected = $('#dropdown_selected_' + dropdown_id);
  var newText = $('#dropdown_' + dropdown_id + '-option-' + option_id).text();
  oldSelected.text(newText);
  if(newText.indexOf("BGS") > -1 ){
      window.chart.reference = "BGS";
  } else if(newText.indexOf("MSL") > -1 ){
      window.chart.reference = "MSL";
  }

  nextTabActive();
  changeGraphs('dropdown_' + dropdown_id)({ value: $.trim(newText) }, undefined, true);
}


function clickGraphPoint(event){
    changeGraphs('graph')(event[0].point);
}


$(document).ready(
    function() {
        try {loadDatePicker();} catch(e) {
            console.log("No date picker available, date picker not loaded", e);
        }
        try {loadSpinner(window.spinnersLength);} catch(e) {
            console.log("No spinner available, spinner not loaded", e);
        }
    }
);
