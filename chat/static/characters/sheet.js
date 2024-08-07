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
var speedInput = $(".speed-input")[0];
var levelInput = $(".level-input")[0];

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

i = 0;
for (const customSubclass in classes){
    customClass.innerHTML += '<option value="' + i + '">' + customSubclass + '</option>';
    i += 1;
}

i = 0;
for (const customSubrace in races){
    customRace.innerHTML += '<option value="' + i + '">' + customSubrace + '</option>';
    i += 1;
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
curData = {}
function updateData(){
    curData["character_name"] = characterName.value;
    curData["custom_class"] = $(customClass).find('option:selected')[0].innerHTML;
    curData["custom_race"] = $(customRace).find('option:selected')[0].innerHTML;
    curData["level"] = parseInt(levelInput.value);
    var stats = ["str", "dex", "cos", "int", "wis", "cha"]
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
    curData["perception"] = perceptionInput.value;
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
    curData["success"] = $($(".d-and-d-save-success")[0]).find(".d-and-d-skill-circle .active").length;
    curData["failure"] = $($(".d-and-d-save-failure")[0]).find(".d-and-d-skill-circle .active").length;
}

function loadData(){
    characterName.value = curData["character_name"];
    $(customClass).val(curData["custom_class"]);
    $(customRace).val(curData["custom_race"]);
    levelInput.value = curData["level"];
    var stats = ["str", "dex", "cos", "int", "wis", "cha"]
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
    perceptionInput.value = curData["perception"];
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
