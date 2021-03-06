function getPartisanCode(code){
	return code.replace("[","").replace("]","")
}

function prettyPartisan(code){
	if (code == "3686") return "Center";
	else if (code == "3687") return "Center Left";
	else if (code == "3689") return "Left";
	else if (code == "3688") return "Center Right";
	else if (code == "3690") return "Right";
	else return "unknown";
}

function partisanColor(code){
	if (code == "3686") return "gray";
	else if (code == "3687") return "#586af1";
	else if (code == "3689") return "blue";
	else if (code == "3688") return "#ee597c";
	else if (code == "3690") return "red";
	else return "gray";
}

function make(root) {


	var margin = {top: 10, right: 10, bottom: 10, left: 10},
  width = 2000,
  height = 1000;
	// append the svg object to the body of the page
	

var svg = d3.select("#my_dataviz")
	.append("svg")
  		.attr("preserveAspectRatio", "xMinYMin meet")
  		.attr("viewBox", "0 -150 3000 2000")
    	.classed("svg-content", true)
	.append("g")
  	.attr("transform",
        "translate(" + margin.left + "," + margin.top + ")");


	var div = d3.select("body").append("div")   
    	.attr("class", "tooltip")               
    	.style("opacity", 0);

	svg
    .selectAll("rect")
    .data(root.leaves())
    .enter()
    .append('defs')
    .append('pattern')
		.attr('id', function (d) { return d.data.d_hash; })
		.attr('patternUnits', 'userSpaceOnUse')
		//.attr('transform', function (d) { return 'translate(-' + d.x0 + ', ' + d.y0 + ')'}) // need to translate and scale b/c not filling rect 
		.style("fill","grey")
				.attr('width', "100px")
		.attr('height', "100px")
	.append("image")
		.attr("xlink:href", function(d){ return d.data.image_url})
		//.attr('transform', function (d) { return 'translate(-' + d.x0 + ', ' + d.y0 + ')'}) // need to translate and scale b/c not filling rect 
		.attr('width', "100px")
		.attr('height', "100px")
		.attr('object-fill', "fill")
		.style("fill","grey")
		.style("opacity", .9);

	svg
    .selectAll("rect")
    .data(root.leaves())
    .enter()
    .append("rect")
	  .attr('x', function (d) { return d.x0; })
	  .attr('y', function (d) { return d.y0; })
	  .attr('width', function (d) { return d.x1 - d.x0; })
	  .attr('height', function (d) { return d.y1 - d.y0; })
	  .attr('object-fill', "fill")
	  .style("stroke", function (d) { return partisanColor(getPartisanCode(d.data.partisan)) })
	  .style("stroke-width", "6")
	  .style("fill", function (d) { return 'url(#' + d.data.d_hash + ') red'; }) // can't set repeat etc
	  .on("click", function(d){
	  	window.open(d.data.story_url,'_blank'); ;
	  })
	  .on("mouseover", function(d){
			div.transition()        
				.duration(200)      
				.style("opacity", .9);     
			 

			div .html("<img class='overlay' src='"+ d.data.image_url + "' /><br/><h3>"  + d.data.story_title + "<br /><h3> from " + d.data.media_name + "<br /><h4>Published on: " + d.data.publish_date + "</h4><h4>"  + d.data.inlink_count + " Inlinks over week,  "  + d.data.fb_count + " FB Shares over all</h4><br/>Partisan category: "  + prettyPartisan(getPartisanCode(d.data.partisan)))  
				.style("left", (d3.event.pageX) + "px")     
				.style("top", (d3.event.pageY - 28) + "px");		
				//.style("cursor","pointer");   
		})
		.on("mouseout", function(d){
			div.transition()        
				.duration(500)      
				.style("opacity", 0);
		});
      
    svg
    	.selectAll("text")
    	.data(root.leaves())
    	.enter()
    	.append("text")
		  .attr("x", function(d){ return d.x0+5})    // +10 to adjust position (more right)
		  .attr("y", function(d){ return d.y0+20})    // +20 to adjust position (lower)
		  .text(function(d){ return d.data.media_url })
		  .attr("font-size", "15px")
		  .attr("fill", "white")
		  
}


function ready(root) {
  // Then d3.treemap computes the position of each element of the hierarchy
  // The coordinates are added to the root object above
    width = 2000,
  	height = 1000;
  	d3.treemap()
    	.size([width, height])
    	.padding(4)
    	(root);
    
	make(root);
}


function readyInlinks(err, data) {
	if (err) throw err;
	 // Give the data to this cluster layout:
	  // stratify the data: reformatting for d3.js
  	var root = d3.stratify()
    	.id(function(d) { return d.d_hash; })   // Name of the entity (column name is name in csv)
    	.parentId(function(d) { return d.parent; })   // Name of the parent (column name is parent in csv)
    	(data);
    	
  	root.sum(function(d) { return +d.inlink_count }) ;  // Compute the numeric value for each entity

	ready(root)
}


function readyFB(err, data) {
	if (err) throw err;
	 // Give the data to this cluster layout:
	  // stratify the data: reformatting for d3.js
  	var root = d3.stratify()
    	.id(function(d) { return d.d_hash; })   // Name of the entity (column name is name in csv)
    	.parentId(function(d) { return d.parent; })   // Name of the parent (column name is parent in csv)
    	(data);
    	
  	root.sum(function(d) { return +d.fb_count }) ;  // Compute the numeric value for each entity
  	
  	ready(root)
}