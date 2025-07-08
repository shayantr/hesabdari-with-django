// Globally declare the array
// If your javascript isn't refreshed each time you visit the inputs, you'll want to clear this on form submit
array = []

// Add New file
// Replace current file
$("input").change(function(event) {
   let file_list = event.target.files
   let key = event.target.id

   // When we change the files in our input, we persist the file by input
   // Persistence before assignment will always result in the most recent file choice
   persist_file(array, file_list, key)

   // Assign the targets files to whatever is persisted for it
   event.target.files = element_for(array, key).file_list
});

// @doc Pushes or Replaces {key: <key>, file_list: <FileList>} objects into an array
function persist_file(array, file_list, key) {
 if(file_list.length > 0) {
   if(member(array, key)) {
     element_for(array, key).file_list = file_list;
    }else {
     array.push({key: key, file_list: file_list})
    }
  }
}

// @doc Determines if the <key> exists in an object element of the <array>
function member(array, key) {
  return array.some((element, index) => {
    return element.key == key
  })
}

// @doc Get element in array by key
function element_for(array, key) {
  return array.find((function(obj, index) {return obj.key === key}))
}
