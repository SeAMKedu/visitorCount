function startConnect(){

    clientID = "clientID - "+parseInt(Math.random() * 100);

    host = document.getElementById("host").value;   
    port = document.getElementById("port").value;  
    userId  = document.getElementById("username").value;  
    passwordId = document.getElementById("password").value;  

    document.getElementById("messages").innerHTML += "<span> Connecting to " + host + " on port " +port+"</span><br>";
    document.getElementById("messages").innerHTML += "<span> Using the client Id " + clientID +" </span><br>";

    client = new Paho.MQTT.Client(host,Number(port),clientID);

    client.onConnectionLost = onConnectionLost;
    client.onMessageArrived = onMessageArrived;
    client.onConnect = onConnect;
    //client.useSSL;

    client.connect({
        onSuccess: onConnect,
        useSSL: false,
        userName: userId,
        password: passwordId
    });
}

function onConnect(){
    topic =  document.getElementById("topic_s").value;
    document.getElementById("messages").innerHTML += "<span> Subscribing to topic "+topic + "</span><br>";
    client.subscribe(topic, {qos:0});
    document.getElementById("connectbtn").style="display:none"
    document.getElementById("disconnectbtn").style="display:inline"
}

function onConnectionLost(responseObject){
    document.getElementById("messages").innerHTML += "<span> ERROR: Connection is lost.</span><br>";
    if(responseObject !=0){
        document.getElementById("messages").innerHTML += "<span> ERROR:"+ responseObject.errorMessage +"</span><br>";
    }
    document.getElementById("connectbtn").style="display:inline"
    document.getElementById("disconnectbtn").style="display:none"

}

function onMessageArrived(message){
    if(message.destinationName == "pic"){
        console.log("picture OnMessageArrived: ");
        document.getElementById("image").src = "data:image/jpg;base64," + message.payloadString;
    }
    else if(message.destinationName == "stats/fps"){
        document.getElementById("fps").innerText = message.payloadString;
    }
    else if(message.destinationName == "stats/tempUpList"){
        document.getElementById("uplist").innerText = message.payloadString;
    }
    else if(message.destinationName =="stats/tempDownList"){
        document.getElementById("downlist").innerText = message.payloadString;
    }
    else{
        console.log("OnMessageArrived: "+message.payloadString);
        document.getElementById("messages").innerHTML += "<span> Topic:"+message.destinationName+" | Message : "+message.payloadString + "</span><br>";
    }
}

function startDisconnect(){
    client.disconnect();
    document.getElementById("messages").innerHTML += "<span> Disconnected. </span><br>";

}

function publishMessage(){
msg = document.getElementById("Message").value;
topic = document.getElementById("topic_p").value;

Message = new Paho.MQTT.Message(msg);
Message.destinationName = topic;

client.send(Message);
document.getElementById("messages").innerHTML += "<span> Message to topic "+topic+" is sent </span><br>";

}
