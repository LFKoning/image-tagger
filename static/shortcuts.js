shortcuts = {}

document.onkeyup = function(e) {
  e = e || window.event;
  //let key = String.fromCharCode(e.key);

  console.log(e.key)

  if (e.key == "Enter") {
    // Submit with Enter
    document.getElementById("tag_form").submit();
  }
  else if (e.key == "ArrowLeft") {
      // Previous image with left arrow
    document.getElementById("prev_img").click();
  }
  else if (e.key == "ArrowRight") {
      // Next image with right arrow
    document.getElementById("next_img").click();
  }
  else if (e.key in shortcuts) {
    console.log("Found key in shortcuts...")
    console.log(shortcuts)
    console.log(shortcuts[e.key])
    let el = document.getElementById(shortcuts[e.key]);
    el.checked = !el.checked;
  }
};