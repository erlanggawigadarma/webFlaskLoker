document.addEventListener("DOMContentLoaded", function () {
    // Event listener untuk tombol like
    document.querySelectorAll(".like-btn").forEach(button => {
        button.addEventListener("click", function () {
            const jobId = this.dataset.jobId; // Ambil job ID dari data attribute
            toggleLike(jobId, this);
        });
    });

    // Event listener untuk form komentar (hanya jika ada)
    const commentForm = document.getElementById("commentForm");
    if (commentForm) {
        commentForm.addEventListener("submit", function (e) {
            e.preventDefault();
            submitComment();
        });
    }
});

function toggleLike(jobId, button) {
    fetch(`/like/${jobId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        // Update tampilan tombol like
        button.classList.toggle("btn-danger", data.liked);
        button.classList.toggle("btn-outline-dark", !data.liked);

        // Perbarui jumlah like di dalam tombol
        button.querySelector(".like-count").textContent = data.like_count;
    })
    .catch(error => console.error("Error:", error));
}

function submitComment() {
    let job_id = document.getElementById("job_id").value;
    let comment = document.getElementById("comment").value;

    fetch("/comment", {
        method: "POST",
        body: new URLSearchParams({ job_id: job_id, comment: comment }),
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            let commentList = document.getElementById("commentList");
            let newComment = document.createElement("li");
            newComment.innerHTML = `<strong>${data.first_name}:</strong> ${data.comment}`;
            commentList.prepend(newComment);
            document.getElementById("comment").value = "";
        }
    })
    .catch(error => console.error("Error:", error));
}


