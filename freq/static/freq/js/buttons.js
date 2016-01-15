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
        trend_detection: 'periodic_fluctuations',
        periodic_fluctuations: 'autoregressive'
    }[window.active];
    if(nextTab != undefined){
        $('[aria-controls="' + nextTab + '"]').removeClass('disabled');
        $('[aria-controls="' + nextTab + '"] > a').attr('href', '/' + nextTab);
    }
}

function changeGraphs(buttonType, altValue, changeTabs){
    return function(value){
        spinnerShow()
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


function updateGraphs(data){
    var graphs = data.graphs;
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
    } else {
        chart.removeClass('show').addClass('hidden');
    }
    if(window.active == 'periodic_fluctuations'){
        window.charts[0].xAxis.tickFormat(function(d) {return d});
    };
    for(var i=0; i < graphs.length; i++ ){
        var graph = graphs[i];
        d3.select(graph.name).datum(graph.data).call(window.charts[i]);
    }
    spinnerClear();
}

function spinnerShow(){};

function spinnerClear(){};

function setDate(startDate, endDate){
    console.log("startDate, endDate", startDate, endDate);
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
        endDate: 'd',
        viewMode: 'years'
    });
    setDate(window.startpage.startDate, window.startpage.endDate);
    daterange.change(changeDate);
}


function loadSpinner(range){
    for(var i=0; i < range; i++){
        $('#spinner_' + i).spinner().change(changeGraphs('spinner_' + i, spinnerValue(i), true));
    }
        // hier setTimeout(function() gebruiken! en even checken of
        // het direct werkt. Anders boolean zetten die daarbuiten
        // ook gezet wordt.
}


function clickDropDown(dropdown_id, option_id){
    var options = true;
    var i = 0;
    var oldSelected = $('#dropdown_selected_' + dropdown_id);
    var dropdowns = [oldSelected.text()];
    var newText = $('#dropdown_' + dropdown_id + '-option-' + option_id).text();
    oldSelected.text(newText);
    while(options) {
        var dropdown = $('#dropdown_' + dropdown_id + '-option-' + i);
        if(dropdown.length) {
            dropdowns.push(dropdown.text());
        } else {
            options = false
        }
        i++;
    }
    dropdowns = dropdowns.slice(0, option_id + 1).concat(
        dropdowns.slice(option_id + 2, dropdowns.length));
    dropdowns.sort();
    for(var i=0; i < dropdowns.length; i++){
        $('#dropdown_' + dropdown_id + '-option-' + i).text(dropdowns[i])
    }
    nextTabActive()
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
