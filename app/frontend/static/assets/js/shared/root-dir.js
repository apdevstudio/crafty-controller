
function show_file_tree() {
    $("#dir_select").modal();
}
function getDirView(event = false) {
    if (event) {
        try {
            let path = event.target.parentElement.getAttribute('data-path');
            if (event.target.parentElement.classList.contains('clicked')) {

                if ($(`#${path}span`).hasClass('files-tree-title')) {
                    $(`#${path}ul`).toggleClass("d-block");
                    $(`#${path}span`).toggleClass("tree-caret-down");
                }
                return;
            } else {
                getTreeView(path);
            }
        } catch {
            console.log("Well that failed");
        }
    } else if ($("#root_files_button").hasClass("clicked")) {
        getTreeView($("#zip_server_path").val(), true);
    } else {
        getTreeView($("#file-uploaded").val(), true, true);
    }
}


async function getTreeView(path, unzip = false, upload = false) {
    const token = getCookie("_xsrf");
    console.log("IN TREE VIEW")
    console.log({ "page": "import", "folder": path, "upload": upload, "unzip": unzip });
    let res = await fetch(`/api/v2/import/file/unzip/`, {
        method: 'POST',
        headers: {
            'X-XSRFToken': token
        },
        body: JSON.stringify({ "page": "import", "folder": path, "upload": upload, "unzip": unzip }),
    });
    let responseData = await res.json();
    if (responseData.status === "ok") {
        console.log(responseData);
        process_tree_response(responseData);
        let x = document.querySelector('.bootbox');
        if (x) {
            x.remove()
        }
        x = document.querySelector('.modal-backdrop');
        if (x) {
            x.remove()
        }
        show_file_tree();

    } else {

        bootbox.alert({
            title: responseData.status,
            message: responseData.error
        });
    }
}

function process_tree_response(response) {
    const styles = window.getComputedStyle(document.getElementById("lower_half"));
    //If this value is still hidden we know the user is executing a zip import and not an upload
    if (styles.visibility === "hidden") {
        document.getElementById('zip_submit').disabled = false;
    } else {
        document.getElementById('upload_submit').disabled = false;
    }
    let path = response.data.root_path.path;
    $(".root-input").val(response.data.root_path.path);
    let text = `<ul class="tree-nested d-block" id="${path}ul">`;
    Object.entries(response.data).forEach(([key, value]) => {
        if (key === "root_path" || key === "db_stats") {
            //continue is not valid in for each. Return acts as a continue.
            return;
        }

        let dpath = value.path;
        let filename = key;
        if (value.dir) {
            text += `<li class="tree-item" id="${dpath}li"  data-path="${dpath}">
                    <div id="${dpath}" data-path="${dpath}" data-name="${filename}" class="tree-caret tree-ctx-item tree-folder">
                    <input type="radio" name="root_path" value="${dpath}">
                    <span id="${dpath}span" class="files-tree-title" data-path="${dpath}" data-name="${filename}" onclick="getDirView(event)">
                      <i style="color: var(--info);" class="far fa-folder"></i>
                      <i style="color: var(--info);" class="far fa-folder-open"></i>
                      ${filename}
                      </span>
                    </input></div><li>`
        } else {
            text += `<li
          class="d-block tree-ctx-item tree-file"
          data-path="${dpath}"
          data-name="${filename}"
          onclick="" id="${dpath}li"><input type='radio' class="checkBoxClass d-none file-check" name='root_path' value="${dpath}" disabled><span style="margin-right: 6px;">
          <i class="far fa-file"></i></span></input>${filename}</li>
      `
        }
    });
    text += `</ul>`;

    if (response.data.root_path.top) {
        try {
            document.getElementById('main-tree-div').innerHTML += text;
            document.getElementById('main-tree').parentElement.classList.add("clicked");
        } catch {
            document.getElementById('files-tree').innerHTML = text;
        }
    } else {
        try {
            document.getElementById(path + "span").classList.add('tree-caret-down');
            document.getElementById(path).innerHTML += text;
            document.getElementById(path).classList.add("clicked");
        } catch {
            console.log("Bad")
        }

        let toggler = document.getElementById(path + "span");

        if (toggler.classList.contains('files-tree-title')) {
            document.getElementById(path + "span").addEventListener("click", function caretListener() {
                document.getElementById(path + "ul").classList.toggle("d-block");
                document.getElementById(path + "span").classList.toggle("tree-caret-down");
            });
        }
    }
}

function getToggleMain(event) {
    path = event.target.parentElement.getAttribute('data-path');
    document.getElementById("files-tree").classList.toggle("d-block");
    document.getElementById(path + "span").classList.toggle("tree-caret-down");
    document.getElementById(path + "span").classList.toggle("tree-caret");
}