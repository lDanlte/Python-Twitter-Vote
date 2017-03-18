/**
 * Created by denis.antonov on 05.03.17.
 */


var tweetUrlPattern = /https?:\/\/twitter\.com\/(?:#!\/)?(\w+)\/status(es)?\/(\d+)/g;
var tweetHolder = $("#tweetHolder");
var tweetInput = $("#tweetUrl");
var voteButtons = $("#voteButtonsHolder");
var likeButton = $("#likeButton");
var dislikeButton = $("#dislikeButton");
var likesCount = $("#likesCount");
var dislikesCount = $("#dislikesCount");

var currentTweet;


twttr.ready(
  function (twttr) {
      twttr.events.bind("rendered", function (event) {
          tweetHolder.show();
          loadVotes(currentTweet);
      });
  }
);


function loadTweet() {
    var tweetUrl = tweetInput.val();
    if (tweetUrl == currentTweet) {
        return;
    }
    var isMatch = tweetUrl.match(tweetUrlPattern);

    if (!isMatch) {
        tweetInput.addClass("error");
        setTimeout(function () {
          tweetInput.removeClass("error");
        }, 1600);
        return;
    }

    $.ajax({
        url: "https://publish.twitter.com/oembed",
        method: "GET",
        dataType: "jsonp",
        data: {
            url: tweetUrl,
            omit_script: true,
            lang: getCookie("lang")
        },
        success: function(data) {
            tweetHolder.hide();
            tweetHolder.html(data.html);
            twttr.widgets.load(tweetHolder);
            currentTweet = tweetUrl;
        },
        error: function (jqXHR, textStatus, errorThrown) {
            alert("response status " + errorThrown);
        }
    });

}

function loadVotes(tweetUrl) {
    voteButtons.hide();

    $.ajax({
        url: "/ui/load_votes?tweet_id=" + getTweetId(tweetUrl),
        method: "GET",
        dataType: "json",
        success: function (data) {
            updateVoteState(data);
            voteButtons.show();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            if (jqXHR.status == 404) {
                updateVoteState({
                    "likesCount": 0,
                    "dislikesCount": 0,
                    "userVote": "non"
                });
                voteButtons.show();
                return;
            }
            alert("response status " + errorThrown);
        }

    })

}

function updateVoteState(data) {
    likeButton.removeClass("selected");
    dislikeButton.removeClass("selected");
    likesCount.html(data.likesCount);
    dislikesCount.html(data.dislikesCount);


    switch (data.userVote){
        case "like":
            likeButton.addClass("selected");
            break;
        case "dislike":
            dislikeButton.addClass("selected");
            break;
    }
}

//voteStatus maybe 'like' or 'dislike'
function vote(voteStatus) {
    var isRemoveVote = false;
    switch (voteStatus) {
        case 'like':
            isRemoveVote = likeButton.hasClass("selected");
            break;
        case 'dislike':
            isRemoveVote = dislikeButton.hasClass("selected");
            break;
    }
    if (isRemoveVote) {
        $.ajax({
            url: "/ui/remove_vote",
            method: "POST",
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify({
                tweetId: getTweetId(currentTweet)
            }),
            success: updateVoteState,
            error: function (jqXHR, textStatus, errorThrown) {
                alert("response status " + errorThrown);
            }
        });
    } else {
        $.ajax({
            url: "/ui/vote",
            method: "POST",
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify({
                tweetId: getTweetId(currentTweet),
                voteStatus: voteStatus
            }),
            success: updateVoteState,
            error: function (jqXHR, textStatus, errorThrown) {
                alert("response status " + errorThrown);
            }
        });
    }
}

function getTweetId(tweetUrl) {
    return tweetUrl.substring(tweetUrl.lastIndexOf("/") + 1)
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}