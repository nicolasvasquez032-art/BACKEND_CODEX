/*
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
var showControllersOnly = false;
var seriesFilter = "";
var filtersOnlySampleSeries = true;

/*
 * Add header in statistics table to group metrics by category
 * format
 *
 */
function summaryTableHeader(header) {
    var newRow = header.insertRow(-1);
    newRow.className = "tablesorter-no-sort";
    var cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Requests";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 3;
    cell.innerHTML = "Executions";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 7;
    cell.innerHTML = "Response Times (ms)";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Throughput";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 2;
    cell.innerHTML = "Network (KB/sec)";
    newRow.appendChild(cell);
}

/*
 * Populates the table identified by id parameter with the specified data and
 * format
 *
 */
function createTable(table, info, formatter, defaultSorts, seriesIndex, headerCreator) {
    var tableRef = table[0];

    // Create header and populate it with data.titles array
    var header = tableRef.createTHead();

    // Call callback is available
    if(headerCreator) {
        headerCreator(header);
    }

    var newRow = header.insertRow(-1);
    for (var index = 0; index < info.titles.length; index++) {
        var cell = document.createElement('th');
        cell.innerHTML = info.titles[index];
        newRow.appendChild(cell);
    }

    var tBody;

    // Create overall body if defined
    if(info.overall){
        tBody = document.createElement('tbody');
        tBody.className = "tablesorter-no-sort";
        tableRef.appendChild(tBody);
        var newRow = tBody.insertRow(-1);
        var data = info.overall.data;
        for(var index=0;index < data.length; index++){
            var cell = newRow.insertCell(-1);
            cell.innerHTML = formatter ? formatter(index, data[index]): data[index];
        }
    }

    // Create regular body
    tBody = document.createElement('tbody');
    tableRef.appendChild(tBody);

    var regexp;
    if(seriesFilter) {
        regexp = new RegExp(seriesFilter, 'i');
    }
    // Populate body with data.items array
    for(var index=0; index < info.items.length; index++){
        var item = info.items[index];
        if((!regexp || filtersOnlySampleSeries && !info.supportsControllersDiscrimination || regexp.test(item.data[seriesIndex]))
                &&
                (!showControllersOnly || !info.supportsControllersDiscrimination || item.isController)){
            if(item.data.length > 0) {
                var newRow = tBody.insertRow(-1);
                for(var col=0; col < item.data.length; col++){
                    var cell = newRow.insertCell(-1);
                    cell.innerHTML = formatter ? formatter(col, item.data[col]) : item.data[col];
                }
            }
        }
    }

    // Add support of columns sort
    table.tablesorter({sortList : defaultSorts});
}

$(document).ready(function() {

    // Customize table sorter default options
    $.extend( $.tablesorter.defaults, {
        theme: 'blue',
        cssInfoBlock: "tablesorter-no-sort",
        widthFixed: true,
        widgets: ['zebra']
    });

    var data = {"OkPercent": 21.65231727422605, "KoPercent": 78.34768272577395};
    var dataset = [
        {
            "label" : "FAIL",
            "data" : data.KoPercent,
            "color" : "#FF6347"
        },
        {
            "label" : "PASS",
            "data" : data.OkPercent,
            "color" : "#9ACD32"
        }];
    $.plot($("#flot-requests-summary"), dataset, {
        series : {
            pie : {
                show : true,
                radius : 1,
                label : {
                    show : true,
                    radius : 3 / 4,
                    formatter : function(label, series) {
                        return '<div style="font-size:8pt;text-align:center;padding:2px;color:white;">'
                            + label
                            + '<br/>'
                            + Math.round10(series.percent, -2)
                            + '%</div>';
                    },
                    background : {
                        opacity : 0.5,
                        color : '#000'
                    }
                }
            }
        },
        legend : {
            show : true
        }
    });

    // Creates APDEX table
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.1533705806924345, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [0.9976415094339622, 500, 1500, "[GET] 03 - Filtrar y Paginar Vacantes"], "isController": false}, {"data": [1.0, 500, 1500, "[POST] 04 - Auth Login (Evaluación de Hashing y Rate Limit)"], "isController": false}, {"data": [0.07458819174532667, 500, 1500, "[GET] 01 - Health Check"], "isController": false}, {"data": [0.0938701409653994, 500, 1500, "[GET] 02 - Listar Vacantes Generales"], "isController": false}]}, function(index, item){
        switch(index){
            case 0:
                item = item.toFixed(3);
                break;
            case 1:
            case 2:
                item = formatDuration(item);
                break;
        }
        return item;
    }, [[0, 0]], 3);

    // Create statistics table
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 10918, 8554, 78.34768272577395, 5551.185748305564, 96, 29110, 5005.0, 8613.1, 9612.05, 17931.43, 374.7511498592709, 1199.7452436907909, 16.863217160362463], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["[GET] 03 - Filtrar y Paginar Vacantes", 424, 0, 0.0, 180.72405660377356, 105, 1675, 178.0, 241.5, 267.75, 310.75, 54.16453755748594, 133.71870209504343, 11.107961803781297], "isController": false}, {"data": ["[POST] 04 - Auth Login (Evaluación de Hashing y Rate Limit)", 409, 0, 0.0, 134.22249388753067, 97, 312, 123.0, 187.0, 203.0, 250.0999999999998, 57.29896329504062, 18.017838067385824, 16.395113520944243], "isController": false}, {"data": ["[GET] 01 - Health Check", 5403, 4765, 88.19174532667037, 6200.219692763293, 96, 29110, 5392.0, 9208.6, 9885.800000000007, 19861.640000000014, 185.453422118487, 500.0383129998455, 4.0846417630603415], "isController": false}, {"data": ["[GET] 02 - Listar Vacantes Generales", 4682, 3789, 80.92695429303717, 5761.754592054693, 104, 20546, 5005.0, 8487.0, 9365.699999999999, 15889.13000000005, 189.0418702305487, 775.6248391256511, 6.795718912766988], "isController": false}]}, function(index, item){
        switch(index){
            // Errors pct
            case 3:
                item = item.toFixed(2) + '%';
                break;
            // Mean
            case 4:
            // Mean
            case 7:
            // Median
            case 8:
            // Percentile 1
            case 9:
            // Percentile 2
            case 10:
            // Percentile 3
            case 11:
            // Throughput
            case 12:
            // Kbytes/s
            case 13:
            // Sent Kbytes/s
                item = item.toFixed(2);
                break;
        }
        return item;
    }, [[0, 0]], 0, summaryTableHeader);

    // Create error table
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 111, 1.2976385316810848, 1.016669719728888], "isController": false}, {"data": ["Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 4338, 50.71311667056348, 39.73255174940465], "isController": false}, {"data": ["Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 4037, 47.19429506663549, 36.97563656347317], "isController": false}, {"data": ["Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 68, 0.7949497311199439, 0.6228246931672468], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 10918, 8554, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 4338, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 4037, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 111, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 68, "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": ["[GET] 01 - Health Check", 5403, 4765, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 2640, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 2046, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 65, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 14, "", ""], "isController": false}, {"data": ["[GET] 02 - Listar Vacantes Generales", 4682, 3789, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Connect timed out", 2292, "Non HTTP response code: org.apache.http.conn.ConnectTimeoutException/Non HTTP response message: Connect to talentmatch-api.duckdns.org:443 [talentmatch-api.duckdns.org/18.191.162.235] failed: Read timed out", 1397, "Non HTTP response code: java.net.SocketException/Non HTTP response message: Connection reset", 97, "Non HTTP response code: java.net.SocketTimeoutException/Non HTTP response message: Read timed out", 3, "", ""], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
