var mainStats = $('.main-stats').find(".main-stat");
var skills = $('.skills-container').find('.d-and-d-skill');
var savingThrows = $('.saving-throws-container').find('.d-and-d-skill');
var proficiencyInput = $('.proficiency-input')[0];
var perceptionInput = $('.perception-input')[0];
var customRace = $(".custom-race")[0];
var customClass = $(".custom-class")[0];
var i = 0;
var armourInput = $(".armour-input")[0];
var initiativeInput = $(".initiative-input")[0];
//var speedInput = $(".speed-input")[0];
var levelInput = $(".level-input")[0];
var imgInput = $('#d-and-d-image-factionImg');

var classes = {
    "Бард": [8],
    "Варвар": [12],
    "Плут": [8],
    "Друид": [8]
}

var races = {
    "Эльф": [],
    "Человек": [],
    "Гном": [],
    "Дварф": []
}

for (const customSubclass in classes){
    customClass.innerHTML += '<option value="' + customSubclass + '">' + customSubclass + '</option>';
}

for (const customSubrace in races){
    customRace.innerHTML += '<option value="' + customSubrace + '">' + customSubrace + '</option>';
}

var mainstat2skills = [
    [3],
    [0, 15, 16],
    [],
    [2, 5, 8, 10, 14],
    [1, 6, 9, 11, 17],
    [4, 7, 12, 13]
]


proficiencies = $(".proficiencies")[0];
currentHit = $(".current-hit")[0];
attacksSpellcasting = $(".attacks-spellcasting")[0];
equipment = $(".equipment")[0];
personalityTraits = $(".personality-traits")[0];
ideals = $(".ideals")[0];
bonds = $(".bonds")[0];
flaws = $(".flaws")[0];
featuresTraits = $(".features-traits")[0];
characterName = $(".character-name")[0];
var curData = {};

function updateData(){
    curData["name"] = characterName.value;
    curData["custom_class"] = $(customClass).find('option:selected')[0].innerHTML;
    curData["custom_race"] = $(customRace).find('option:selected')[0].innerHTML;
    curData["level"] = parseInt(levelInput.value);
    var stats = ["stre", "dex", "cos", "inte", "wis", "cha"]
    i = 0;
    for (var stat of stats){
        curData[stat] = parseInt($(mainStats[i]).find(".d-and-d-statbox-modifier")[0].innerHTML);
        i += 1;
    }
    i = 0;
    for (var stat of stats){
        curData[stat + "_down"] = parseInt($(mainStats[i]).find("input")[0].value);
        i += 1;
    }
    curData["proficiency_bonus"] = proficiencyInput.value;
    curData["passive_perception"] = perceptionInput.value;
    i = 0;
    for (var stat of stats){
        curData[stat + "_saving"] = parseInt($(savingThrows[i]).find("input")[0].value);
        i += 1;
    }
    var skillTypes = ["acrobatics", "animals", "arcana", "athletics", 
        "deception", "history", "insight", "intimidation", "investigation",
        "medicine", "nature", "perception", "performance", "persuasion",
        "religion", "sleightofhand", "stealth", "survival"];
    i = 0;
    for (var skill of skillTypes){
        curData[skill] = parseInt($(skills[i]).find("input")[0].value);
        i += 1;
    }
    curData["proficiencies"] = proficiencies.value;
    curData["current_hit"] = currentHit.value;
    curData["attacks_spellcasting"] = attacksSpellcasting.value;
    curData["equipment"] = equipment.value;
    curData["personality_traits"] = personalityTraits.value;
    curData["ideals"] = ideals.value;
    curData["bonds"] = bonds.value;
    curData["flaws"] = flaws.value;
    curData["features_traits"] = featuresTraits.value;
    curData["success"] = $($(".d-and-d-save-success")[0]).find(".d-and-d-skill-circle.active").length;
    curData["failure"] = $($(".d-and-d-save-failure")[0]).find(".d-and-d-skill-circle.active").length;
    curData["armour"] = armourInput.value;
    curData["initiative"] = initiativeInput.value;
    curData["speed"] = 30;//speedInput.value;

    const backgroundImage = $('.d-and-d-image')[0].style.backgroundImage;
    const match = backgroundImage.match(/url\("data:image\/[a-zA-Z]+;base64,([^\"]+)"\)/);
    if (match && match[1]) {
        const base64Image = match[1];
        curData["image"] = base64Image;
    } else {
        curData["image"] = "";
        console.log('No base64 image found');
    }
}

function loadData(){
    characterName.value = curData["name"];
    $(customClass).val(curData["custom_class"]);
    $(customRace).val(curData["custom_race"]);
    levelInput.value = curData["level"];
    var stats = ["stre", "dex", "cos", "inte", "wis", "cha"]
    i = 0;
    for (var stat of stats){
        $(mainStats[i]).find(".d-and-d-statbox-modifier")[0].innerHTML = curData[stat];
        i += 1;
    }
    i = 0;
    for (var stat of stats){
        $(mainStats[i]).find("input")[0].value = curData[stat + "_down"];
        i += 1;
    }
    proficiencyInput.value = curData["proficiency_bonus"];
    perceptionInput.value = curData["passive_perception"];
    i = 0;
    for (var stat of stats){
        $(savingThrows[i]).find("input")[0].value = curData[stat + "_saving"];
        i += 1;
    }
    var skillTypes = ["acrobatics", "animals", "arcana", "athletics", 
        "deception", "history", "insight", "intimidation", "investigation",
        "medicine", "nature", "perception", "performance", "persuasion",
        "religion", "sleightofhand", "stealth", "survival"];
    i = 0;
    for (var skill of skillTypes){
        $(skills[i]).find("input")[0].value = curData[skill];
        i += 1;
    }
    proficiencies.value = curData["proficiencies"];
    currentHit.value = curData["current_hit"];
    attacksSpellcasting.value = curData["attacks_spellcasting"];
    equipment.value = curData["equipment"];
    personalityTraits.value = curData["personality_traits"];
    ideals.value = curData["ideals"];
    bonds.value = curData["bonds"];
    flaws.value = curData["flaws"];
    featuresTraits.value = curData["features_traits"];
    for (let step = 0; step < curData["success"]; step++) {
        $($($(".d-and-d-save-success")[0]).find(".d-and-d-skill-circle")[step]).addClass("active");
    }
    for (let step = 0; step < curData["failure"]; step++) {
        $($($(".d-and-d-save-failure")[0]).find(".d-and-d-skill-circle")[step]).addClass("active");
    }

    armourInput.value = curData["armour"];
    initiativeInput.value = curData["initiative"];
    //speedInput.value = curData["speed"];

    if (curData["image"]){
        $('.d-and-d-image')[0].style.backgroundImage = "url(data:image/png;base64," + curData["image"] + ")";
    }
}

function mainStatChanged(ind, stat2change){
    function out(e){
        var inp = $(this);
        var newval = Math.floor((inp.val() - 10) / 2);
        stat2change.innerHTML = newval;
        for (const skillInd of mainstat2skills[ind]){
            $(skills[skillInd]).find("input")[0].value = newval + parseInt(proficiencyInput.value);
        }
        var classInd = $(customClass).find('option:selected')[0].innerHTML;
        var level = parseInt(levelInput.value);
        if (ind == 1){
            initiativeInput.value = newval + 1;
        }
        if (ind == 2){
            armourInput.value = newval + classes[classInd][0] * level;
        }
    }
    return out;
}

i = 0;
for (const mainStat of mainStats){
    inp = $(mainStat).find("input")[0];
    stat2change = $(mainStat).find(".d-and-d-statbox-modifier")[0];
    
    $(inp).on('input', mainStatChanged(i, stat2change));
    i += 1;
}

function levelChanged(e){
    var inp = $(this);
    level = parseInt(inp.val());
    var constitution = parseInt($(mainStats[2]).find("input")[0].value);
    var classInd = $(customClass).find('option:selected')[0].innerHTML;
    armourInput.value = constitution + classes[classInd][0] * level;
}
$(levelInput).on('input', levelChanged);


function circleClick(circleElem){
    function out(e){
        if ($(circleElem).hasClass("active")) {
            $(circleElem).removeClass("active")
        }else{
            $(circleElem).addClass("active");
        }
    }
    return out;
}
for (const circle of $(".d-and-d-skill-circle")){
    $(circle).on('click', circleClick(circle));
}

$('.d-and-d-image').on('click', function() {
    imgInput.trigger('click');
});

function LoadFile(e) {
    const [file] = e.files;
    if (file) {        
        const FR = new FileReader();
        FR.addEventListener("load", function(evt) {
            $('.d-and-d-image')[0].style.backgroundImage = "url(" + evt.target.result + ")";
        });
        FR.readAsDataURL(file);
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function generateImg() {
    generateBtn.hide();
    const url = window.location.href;
    updateData();
    let data = new FormData();
    data.append("all_data", JSON.stringify(curData));
    data.append("generate", "true");

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: data
        });

        if (response.ok) {
            const jsonResponse = await response.json();
            $('.d-and-d-image')[0].style.backgroundImage = "url(data:image/png;base64," + jsonResponse["img_b64"] + ")";
        } else {
            console.error('Error:', response.statusText);
        }
    } catch (error) {
        console.error('Error:', error);
    }
    generateBtn.show();
}

var createBtn = $(".create-btn")[0];

var generateBtn = $(".generate-btn");
generateBtn.on('click', generateImg);

var characterForm = $(".character-form");
characterForm.on('submit', function(event) {
    event.preventDefault();
    updateData();

    let formData = new FormData(event.target);
    formData.append("all_data", JSON.stringify(curData));
    formData.append("create", "True");

    let xhr = new XMLHttpRequest();
    xhr.open('POST', '/profile/', true);

    xhr.onload = function () {
        window.location.href = '/profile';
        if (xhr.status != 200) {
            console.error('Form submission failed:', xhr.statusText);
        }
    };

    xhr.send(formData);
});